"""Authentification locale : connexion + création de compte (email + mot de passe).

- Les comptes sont dans users.json (non versionné, voir .gitignore).
- Les mots de passe ne sont jamais stockés en clair : PBKDF2-SHA256 + sel aléatoire.
- Après 5 échecs sur un email, il est bloqué 60 secondes (même si on recharge la page).
- Créer un compte : onglet « Créer un compte » de la page de connexion
  (ou python create_user.py / Creer_Compte.bat pour réinitialiser un mot de passe).
"""
import hashlib
import hmac
import json
import re
import secrets
import time
from pathlib import Path

import streamlit as st

USERS_FILE = Path(__file__).resolve().parent / "users.json"
ITERATIONS = 310_000
MAX_TRIES, LOCK_SECONDS = 5, 60
ALLOW_SIGNUP = True  # mettre False si l'app est publiée en ligne (sinon n'importe qui peut créer un compte)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS).hex()


def load_users() -> dict:
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def add_user(email: str, password: str, overwrite: bool = True) -> None:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise ValueError("Email invalide.")
    if len(password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
    users = load_users()
    if email in users and not overwrite:
        raise ValueError("Un compte existe déjà avec cet email.")
    salt = secrets.token_bytes(16)
    users[email] = {"salt": salt.hex(), "hash": _hash(password, salt)}
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def _check(email: str, password: str) -> bool:
    user = load_users().get(email.strip().lower())
    salt = bytes.fromhex(user["salt"]) if user else b"\0" * 16  # même durée si l'email n'existe pas
    ok = hmac.compare_digest(_hash(password, salt), user["hash"] if user else "x")
    return bool(user) and ok


@st.cache_resource
def _attempts() -> dict:
    return {}  # email -> [nb_échecs, bloqué_jusqu'à]


def login_gate(apply_theme) -> None:
    """Affiche la page de connexion et arrête l'app tant que l'utilisateur n'est pas connecté."""
    if st.session_state.get("auth_user"):
        return
    apply_theme()
    st.markdown("<div style='height:9vh'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.15, 1])
    with mid:
        st.markdown('<div class="ems-brand" style="justify-content:center"><div class="ems-logo">⚡</div>'
                    '<div><b>Energy Management</b><span>Connexion sécurisée</span></div></div>',
                    unsafe_allow_html=True)
        tabs = st.tabs(["Se connecter", "Créer un compte"] if ALLOW_SIGNUP else ["Se connecter"])
        with tabs[0]:
            with st.form("login"):
                email = st.text_input("Email", placeholder="nom@exemple.com")
                password = st.text_input("Mot de passe", type="password")
                go = st.form_submit_button("Se connecter", use_container_width=True, type="primary")
            if go:
                key, att = email.strip().lower(), _attempts()
                tries, until = att.get(key, [0, 0.0])
                if time.time() < until:
                    st.error(f"Trop de tentatives. Réessaie dans {int(until - time.time()) + 1} s.")
                elif _check(email, password):
                    att.pop(key, None)
                    st.session_state["auth_user"] = key
                    st.rerun()
                else:
                    tries += 1
                    att[key] = [0 if tries >= MAX_TRIES else tries,
                                time.time() + LOCK_SECONDS if tries >= MAX_TRIES else 0.0]
                    st.error("Email ou mot de passe incorrect.")
        if ALLOW_SIGNUP:
            with tabs[1]:
                with st.form("signup"):
                    s_email = st.text_input("Email", placeholder="nom@exemple.com", key="s_email")
                    s_pw = st.text_input("Mot de passe (8 caractères min.)", type="password", key="s_pw")
                    s_pw2 = st.text_input("Confirmer le mot de passe", type="password", key="s_pw2")
                    sign = st.form_submit_button("Créer mon compte", use_container_width=True, type="primary")
                if sign:
                    if s_pw != s_pw2:
                        st.error("Les deux mots de passe sont différents.")
                    else:
                        try:
                            add_user(s_email, s_pw, overwrite=False)
                            st.session_state["auth_user"] = s_email.strip().lower()
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
    st.stop()


def logout_button() -> None:
    st.sidebar.divider()
    st.sidebar.caption(f"Connecté : {st.session_state['auth_user']}")
    if st.sidebar.button("Se déconnecter", use_container_width=True):
        st.session_state.pop("auth_user", None)
        st.rerun()
