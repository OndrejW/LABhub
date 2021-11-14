#!/usr/bin/python
# -*- coding: utf

from flask_nav import Nav
from flask_nav.elements import Navbar, View, Subgroup


nav = Nav()

nav.register_element(
    "top_menu", Navbar(
        View(u"Home", ".index"), 
        View(u"New log entry", ".addMeasurementLog"),
        View(u"New note", ".addOccasion"),
        Subgroup(
            'Add',
            View(u"Session", ".addSession"),
            View(u"Sample", ".addSample"),
            View(u"Structure", ".addStructure"),
            View(u"Project", ".addProject"),
            View(u"Setup", ".addSetup"),
            View(u"Drawer", ".addDrawer"),
    ),
        Subgroup(
            'List',
            View(u"Session", ".list_session"),
            View(u"Sample", ".list_sample"),
            View(u"Project", ".list_project"),
            View(u"Setup", ".list_setup"),
            View(u"Drawer", ".list_drawer"),
            View(u"Users", ".list_users"),
    ),
        View(u"Tools", ".tools"),
    )
)


nav.register_element(
    "login_menu", Navbar( 
    	View(u"", "."),
        View(u"Login", ".login"),
        View(u"Register", ".register"),
    )
)

nav.register_element(
    "user_menu", Navbar( 
        View(u"", "."),
        View(u"logout", ".logout"),
    )
)

from dominate import tags
from flask_nav.renderers import Renderer

class TopMenuRenderer(Renderer):
    def visit_Navbar(self, node):
        sub = []
        for item in node.items:
            sub.append(self.visit(item))

        return tags.div(*sub, _class = 'navbar-nav mr-auto')

    def visit_View(self, node):
        a = tags.a('{}'.format(node.text), _class = 'nav-item nav-link', href = node.get_url())
        return a

    def visit_Subgroup(self, node):
        # almost the same as visit_Navbar, but written a bit more concise
        div = tags.div( _class = 'nav-item dropdown')
        a = div.add(tags.a(node.title, _class = 'nav-link nav-item dropdown-toggle', id = 'navbardrop'))
        a['data-toggle'] = 'dropdown'

        divDrop = div.add(tags.div(_class = 'dropdown-menu'))

        self._in_dropdown = True
        for item in node.items:
            divDrop.add(tags.a(item.text, _class = 'dropdown-item', href = item.get_url()))
        return div

# ,  *[self.visit(item) for item in node.items]

class RightMenuRenderer(Renderer):
    def visit_Navbar(self, node):
        sub = []
        for item in node.items:
            sub.append(self.visit(item))

        return tags.div('', _class = 'navbar-nav', *sub)

    def visit_View(self, node):
        return tags.a('{}'.format(node.text), _class = 'nav-item nav-link', href = node.get_url())

    def visit_Subgroup(self, node):
        # almost the same as visit_Navbar, but written a bit more concise
        return tags.a(node.title,
                        *[self.visit(item) for item in node.items])