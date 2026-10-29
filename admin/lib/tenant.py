"""Tenant isolation. Wraps the Supabase client so EVERY query on a tenant table is limited to the
signed-in user's rows and every insert is stamped with their owner_id. Existing code in lib/store.py,
lib/indexer.py, lib/search.py keeps working unchanged because it only ever sees the scoped client.
Fails closed: with no signed-in user, any query raises PermissionError."""
import streamlit as st

TENANT_TABLES = {"files", "folders", "topics", "posts", "templates", "chunks", "chat_log"}
TENANT_RPCS = {"match_chunks", "search_chunks", "hybrid_search"}   # <- your search function names; they get p_owner


def current_uid():
    uid = st.session_state.get("uid")
    if not uid:
        raise PermissionError("Not signed in.")
    return uid


class _Table:
    def __init__(self, table, uid):
        self._t, self._uid = table, uid

    def _stamp(self, rows):
        if isinstance(rows, list):
            return [{**r, "owner_id": self._uid} for r in rows]
        return {**rows, "owner_id": self._uid}

    def select(self, *a, **k):
        return self._t.select(*a, **k).eq("owner_id", self._uid)

    def insert(self, rows, **k):
        return self._t.insert(self._stamp(rows), **k)

    def upsert(self, rows, **k):
        return self._t.upsert(self._stamp(rows), **k)

    def update(self, values, **k):
        values = {kk: v for kk, v in values.items() if kk != "owner_id"}   # ownership can never be changed
        return self._t.update(values, **k).eq("owner_id", self._uid)

    def delete(self, **k):
        return self._t.delete(**k).eq("owner_id", self._uid)


class TenantClient:
    def __init__(self, raw, uid):
        self._raw, self._uid = raw, uid

    def table(self, name):
        t = self._raw.table(name)
        return _Table(t, self._uid) if name in TENANT_TABLES else t

    from_ = table

    def rpc(self, fn, params=None, *a, **k):
        if fn in TENANT_RPCS:
            params = {**(params or {}), "p_owner": self._uid}
        return self._raw.rpc(fn, params, *a, **k)

    def __getattr__(self, name):          # storage, auth, etc. pass straight through
        return getattr(self._raw, name)


def scoped(raw_client):
    return TenantClient(raw_client, current_uid())
