#!/usr/bin/python
# -*- coding: utf-8 -*-


from labhub import login_manager
from labhub.lib.site import Site


class User(Site):
    def __init__(self, login, db=None):
        self.login = login

        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

        if db:
            super(User, self).__init__(db)


    def get_id(self):
        return self.login


    def verify(self, password):
        """
        Method verifing user password.
        """
        sql = """
            SELECT
                pswd_hash = crypt(%(password)s, salt) AS hit
            FROM
               operator
            WHERE
                login = %(login)s
        """
        self.c.execute(sql,{
            "login": self.login,
            "password": password
        })
        res = self.c.fetchone() or {}

        return bool(res.get("hit", False))


    def create(self, mail, name, password):
        """
        Create new operator in database.
        """
        sql = """
            INSERT INTO contacts
                (mail)
            VALUES
                (%(mail)s)
            RETURNING
                id
        """
        self.c.execute(sql, {"mail": mail})
        contact_id = self.c.fetchone()["id"]

        self.c.execute("SELECT gen_salt('bf') AS salt")
        salt = self.c.fetchone()["salt"]

        sql = """
            INSERT INTO operator
                (login, name, id_contact, salt, pswd_hash)
            VALUES (
                %(login)s,
                %(name)s,
                %(id_contact)s,
                %(salt)s,
                (SELECT crypt(%(password)s, %(salt)s))
            )
        """
        self.c.execute(sql, {
            "login": self.login,
            "name": name,
            "id_contact": contact_id,
            "salt": salt,
            "password": password
        })

        self.conn.commit()


    def list():
        """
        List all users with their basic info.
        return - list of dicts of users
        """
        pass


@login_manager.user_loader
def user_loader(login):
    return User(login)

