"""Crée (ou met à jour) un compte : python create_user.py"""
import getpass

from auth import add_user

email = input("Email : ").strip()
pw = getpass.getpass("Mot de passe (8 caractères min) : ")
if pw != getpass.getpass("Confirmer le mot de passe : "):
    raise SystemExit("Les mots de passe sont différents.")
try:
    add_user(email, pw)
    print("Compte enregistré dans users.json.")
except ValueError as e:
    raise SystemExit(str(e))
