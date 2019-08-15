# menu.py
import lcd as LCD

# Define globals
DIRECTION_UP = 0
DIRECTION_DOWN = 1
VISIBLE = True
INVISIBLE = False


class MenuItem(object):
    def __init__(self, type, name, attributes=None, visible=True):
        self.type = type
        self.name = name
        self.attributes = attributes
        self.visible = visible


class MenuLink(object):
    def __init__(self, name, parent, child=None, attributes=None):
        self.type = "menu_link"
        self.name = name
        self.parent = parent
        self.child = child
        self.attributes = attributes

    def setParent(self, menu):
        self.parent = menu

    def setChild(self, menu):
        self.child = menu


class Menu(object):
    def __init__(self, name):
        self.type = "menu"
        self.name = name
        self.options = [MenuItem("blank", "")]
        self.selectedOption = 0
        self.parent = None

    def addOptions(self, options):
        self.options = self.options + options
        self.selectedOption = 1

    def addOption(self, option):
        self.options.append(option)
        self.selectedOption = 1

    def setParent(self, parent):
        self.parent = parent

    def nextSelection(self):
        self.selectedOption = (self.selectedOption + 1) % len(self.options)

    def getNextSelection(self):
        return self.options[(self.selectedOption + 1) % len(self.options)]

    def previousSelection(self):
        if (self.selectedOption == 0):
            self.selectedOption = len(self.options) - 1
        else:
            self.selectedOption = self.selectedOption - 1

    def getPreviousSelection(self):
        if (self.selectedOption == 0):
            return self.options[len(self.options) - 1]
        else:
            return self.options[self.selectedOption - 1]

    def getSelection(self):
        return self.options[self.selectedOption]

    def getCurrentMenu(self):
        return self


class MenuContext(object):
    def __init__(self, menu, delegate):
        self.currentMenu = menu
        self.delegate = delegate

    def showMenu(self):
        """
        Shows the menu
        """
        LCD.lcd_blank()
        self.writeMenuHeader()
        self.writeMenuOptions()

    def writeMenuHeader(self):
        LCD.lcd_string(
            self.currentMenu.name,
            LCD.LCD_LINE_1,
            LCD.CENTERED
            )

    def writeMenuOptions(self):
        LCD.lcd_string(
            "  " + self.currentMenu.getPreviousSelection().name,
            LCD.LCD_LINE_2,
            LCD.LEFT_JUSTIFIED
            )
        LCD.lcd_string(
            "* " + self.currentMenu.getSelection().name,
            LCD.LCD_LINE_3,
            LCD.LEFT_JUSTIFIED
            )
        LCD.lcd_string(
            "  " + self.currentMenu.getNextSelection().name,
            LCD.LCD_LINE_4,
            LCD.LEFT_JUSTIFIED
            )

    def setMenu(self, menu):
        """
        Sets a new menu to the menu context.

        raises ValueError if the menu has no options
        """
        if (len(menu.options) == 0):
            raise ValueError("Cannot setMenu on a menu with no options")
        self.currentMenu = menu

    def scroll_up(self):
        """
        Advances the displayed menu to the next visible option

        raises ValueError if all options are visible==False
        """
        self.currentMenu.previousSelection()
        self.showMenu()

    def scroll_down(self):
        """
        Advances the displayed menu to the previous visible option

        raises ValueError if all options are visible==False
        """
        self.currentMenu.previousSelection()
        self.showMenu()

    def retreat(self):
        """
        Retreats the displayed menu to the parent menu

        raises ValueError if parent menu is null
        """
        if (not self.currentMenu.parent):
            raise ValueError("Cannot navigate back when parent is None")
        else:
            self.setMenu(self.currentMenu.parent)
        self.showMenu()

    def select(self):
        """
        Selects the current menu option.
        Calls menuItemClicked first. If it returns false,
        it uses the default logic.
        If true, it calls display with the current selection

        defaults:
            "menu" -> sets submenu as the current menu

        returns True if the default logic should be overridden

        throws ValueError if navigating back on a top-level menu

        """
        selection = self.currentMenu.getSelection()
        if (not self.delegate.menuItemClicked(selection)):
            if (selection.type == "menu"):
                self.setMenu(selection)
                self.showMenu()
            else:
                raise ValueError("Code error, selection type not implemented")


class MenuDelegate(object):
    def menuItemClicked(self, menuItem):
        """
        Called when a menu item is selected.
        Useful for taking action on a menu item click.
        """
        raise NotImplementedError

    def displayMenuItem(self, menuItem):
        """
        Called when the menu item should be displayed.
        """
        raise NotImplementedError
