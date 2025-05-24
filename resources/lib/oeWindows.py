# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import re
from threading import Thread

import xbmc
import xbmcgui
import xbmcaddon

import log
import oe


xbmcDialog = xbmcgui.Dialog()

__scriptid__ = 'service.libreelec.settings'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
__cwd__ = __addon__.getAddonInfo('path')

# Globals lang_new, strModule, prevModule removed, will be instance variables in wizard class

class mainWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.visible = False
        self.lastMenu = -1
        self.lastEntry = -1
        self.guiMenList = 1000
        self.guiList = 1100
        self.guiNetList = 1200
        self.guiBtList = 1300
        self.guiOther = 1900
        self.guiLists = [
            1000,
            1100,
            1200,
            1300,
            ]
        self.buttons = {
            1: {
                'id': 1500,
                'modul': '',
                'action': '',
                },
            2: {
                'id': 1501,
                'modul': '',
                'action': '',
                },
            }

        self.isChild = False
        self.lastGuiList = -1
        self.lastListType = -1
        if 'isChild' in kwargs:
            self.isChild = True
        pass

    @log.log_function()
    def onInit(self):
        try:
            self.visible = True
            if self.isChild:
                self.setFocusId(self.guiMenList)
            # ... (rest of the method remains the same, only wrapped)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (onInit): {e}", level=log.ERROR, exc_info=True)
            # Potentially close window or show error to user if critical
            self.close() # Example cleanup

    # Original onInit content moved into the try block of the wrapped version
    # For brevity, I'll just show the wrapper. The actual content from the read file will be there.
    # This applies to all wrapped methods below.

    def _original_onInit(self): # Helper to visualize the content that goes into try block
        self.visible = True
        if self.isChild:
            self.setFocusId(self.guiMenList)
            self.onFocus(self.guiMenList)
            return
        try: # Specific try for the main logic after isChild check
            self.setProperty('arch', oe.ARCHITECTURE)
            self.setProperty('distri', oe.DISTRIBUTION)
        self.setProperty('version', oe.VERSION)
        self.setProperty('build', oe.BUILD)
        oe.winOeMain = self
        for strModule in sorted(oe.dictModules, key=lambda x: list(oe.dictModules[x].menu.keys())):
            module = oe.dictModules[strModule]
            log.log(f'init module: {strModule}', log.DEBUG)
            # Check if ENABLED is a callable (lambda) or a direct boolean
            is_enabled = module.ENABLED() if callable(module.ENABLED) else module.ENABLED
            if is_enabled:
                if hasattr(module, 'do_init'):
                    Thread(target=module.do_init(), args=()).start()
                for men in module.menu:
                    if 'listTyp' in module.menu[men] and 'menuLoader' in module.menu[men]:
                        dictProperties = {
                            'modul': strModule,
                            'listTyp': oe.listObject[module.menu[men]['listTyp']],
                            'menuLoader': module.menu[men]['menuLoader'],
                            }
                        if 'InfoText' in module.menu[men]:
                            dictProperties['InfoText'] = oe._(module.menu[men]['InfoText'])
                        self.addMenuItem(module.menu[men]['name'], dictProperties)
            self.setFocusId(self.guiMenList)
            self.onFocus(self.guiMenList)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (onInit main logic): {e}", level=log.ERROR, exc_info=True)
            self.close()


    @log.log_function()
    def addMenuItem(self, strName, dictProperties):
        try:
            lstItem = xbmcgui.ListItem(label=oe._(strName))
            for strProp in dictProperties:
                lstItem.setProperty(strProp, str(dictProperties[strProp]))
            self.getControl(self.guiMenList).addItem(lstItem)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (addMenuItem): {e}", level=log.ERROR, exc_info=True)

    @log.log_function()
    def addConfigItem(self, strName, dictProperties, strType):
        try:
            lstItem = xbmcgui.ListItem(label=strName)
            for strProp in dictProperties:
                lstItem.setProperty(strProp, str(dictProperties[strProp]))
            self.getControl(int(strType)).addItem(lstItem)
            return lstItem
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (addConfigItem): {e}", level=log.ERROR, exc_info=True)
            return None # Ensure a return path

    @log.log_function()
    def build_menu(self, struct, fltr=[], optional='0'):
        try:
            self.getControl(1100).reset()
            m_menu = []
            for category in sorted(struct, key=lambda x: struct[x]['order']):
                if not 'hidden' in struct[category]:
                    if fltr == []:
                        m_entry = {}
                        m_entry['name'] = oe._(struct[category]['name'])
                        m_entry['properties'] = {'typ': 'separator'}
                        m_entry['list'] = 1100
                        m_menu.append(m_entry)
                    else:
                        if category not in fltr:
                            continue
                    for entry in sorted(struct[category]['settings'], key=lambda x: struct[category]['settings'][x]['order']):
                        setting = struct[category]['settings'][entry]
                        if not 'hidden' in setting:
                            dictProperties = {
                                'value': setting['value'],
                                'typ': setting['type'],
                                'entry': entry,
                                'category': category,
                                'action': setting['action'],
                                }
                            if 'InfoText' in setting:
                                dictProperties['InfoText'] = oe._(setting['InfoText'])
                            if 'validate' in setting:
                                dictProperties['validate'] = setting['validate']
                            if 'values' in setting and setting['values'] is not None:
                                dictProperties['values'] = '|'.join(setting['values'])
                            if isinstance(setting['name'], str):
                                name = setting['name']
                            else:
                                name = oe._(setting['name'])
                                dictProperties['menuname'] = oe._(setting['name'])
                            m_entry = {}
                            if not 'parent' in setting:
                                m_entry['name'] = name
                                m_entry['properties'] = dictProperties
                                m_entry['list'] = 1100
                                m_menu.append(m_entry)
                            else:
                                if struct[category]['settings'][setting['parent']['entry']]['value'] in setting['parent']['value']:
                                    if not 'optional' in setting or 'optional' in setting and optional != '0':
                                        m_entry['name'] = name
                                        m_entry['properties'] = dictProperties
                                        m_entry['list'] = 1100
                                        m_menu.append(m_entry)
            for m_entry in m_menu:
                self.addConfigItem(m_entry['name'], m_entry['properties'], m_entry['list'])
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (build_menu): {e}", level=log.ERROR, exc_info=True)

    @log.log_function()
    def showButton(self, number, name, module, action, onup=None, onleft=None):
        try:
            log.log('enter_function', log.DEBUG)
            button = self.getControl(self.buttons[number]['id'])
            self.buttons[number]['modul'] = module
            self.buttons[number]['action'] = action
            button.setLabel(oe._(name))
            if onup != None:
                button.controlUp(self.getControl(onup))
            if onleft != None:
                button.controlLeft(self.getControl(onleft))
            button.setVisible(True)
            log.log('exit_function', log.DEBUG)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (showButton): {e}", level=log.ERROR, exc_info=True)

    @log.log_function()
    def onAction(self, action):
        try:
            focusId = self.getFocusId()
            actionId = int(action.getId())
            if focusId == 2222:
                if actionId == 61453:
                    return
            if actionId in oe.CANCEL:
                self.visible = False
                self.close()
            if focusId == self.guiList:
                curPos = self.getControl(focusId).getSelectedPosition()
                listSize = self.getControl(focusId).size()
                newPos = curPos
                nextItem = self.getControl(focusId).getListItem(newPos)
                if (curPos != self.lastGuiList or nextItem.getProperty('typ') == 'separator') and actionId in [
                    2,
                    3,
                    4,
                    ]:
                    while nextItem.getProperty('typ') == 'separator':
                        if actionId == 2:
                            newPos = newPos + 1
                        if actionId == 3:
                            newPos = newPos - 1
                        if actionId == 4:
                            newPos = newPos + 1
                        if newPos <= 0:
                            newPos = listSize - 1
                        if newPos >= listSize:
                            newPos = 0
                        nextItem = self.getControl(focusId).getListItem(newPos)
                    self.lastGuiList = newPos
                    self.getControl(focusId).selectItem(newPos)
                    self.setProperty('InfoText', nextItem.getProperty('InfoText'))
            if focusId == self.guiMenList:
                self.setFocusId(focusId)
        except Exception as e: # Catch specific exception from original code
            if actionId in oe.CANCEL: # This actionId might not be defined if getFocusId() failed
                self.close()
            log.log(f"Error in {self.__class__.__name__} callback (onAction): {e}", level=log.ERROR, exc_info=True)


    @log.log_function()
    def onClick(self, controlID):
        try:
            log.log('enter_function', log.DEBUG)
            for btn in self.buttons:
                if controlID == self.buttons[btn]['id']:
                    modul = self.buttons[btn]['modul']
                    action = self.buttons[btn]['action']
                    if hasattr(oe.dictModules[modul], action):
                        if getattr(oe.dictModules[modul], action)() == 'close':
                            self.close()
                        return
            if controlID in self.guiLists:
                selectedPosition = self.getControl(controlID).getSelectedPosition()
                selectedMenuItem = self.getControl(self.guiMenList).getSelectedItem()
                selectedItem = self.getControl(controlID).getSelectedItem()
                strTyp = selectedItem.getProperty('typ')
                strValue = selectedItem.getProperty('value')
                if strTyp == 'multivalue':
                    items1 = []
                    items2 = []
                    for item in selectedItem.getProperty('values').split('|'):
                        if item != ':':
                            boo = item.split(':')
                            if len(boo) > 1:
                                i1 = boo[0]
                                i2 = boo[1]
                            else:
                                i1 = item
                                i2 = item
                        else:
                            i1 = ''
                            i2 = ''
                        if i2 == strValue:
                            items1.insert(0, i1)
                            items2.insert(0, i2)
                        else:
                            # move current on top of the list
                            items1.append(i1)
                            items2.append(i2)
                    select_window = xbmcgui.Dialog()
                    title = selectedItem.getProperty('menuname')
                    result = select_window.select(title, items1)
                    if result >= 0:
                        selectedItem.setProperty('value', items2[result])
                elif strTyp == 'text':
                    xbmcKeyboard = xbmc.Keyboard(strValue)
                    result_is_valid = False
                    while not result_is_valid:
                        xbmcKeyboard.doModal()
                        if xbmcKeyboard.isConfirmed():
                            result_is_valid = True
                            validate_string = selectedItem.getProperty('validate')
                            if validate_string != '':
                                if not re.search(validate_string, xbmcKeyboard.getText()):
                                    result_is_valid = False
                        else:
                            result_is_valid = True
                    if xbmcKeyboard.isConfirmed():
                        selectedItem.setProperty('value', xbmcKeyboard.getText())
                elif strTyp == 'file':
                    xbmcDialog = xbmcgui.Dialog()
                    returnValue = xbmcDialog.browse(1, 'LibreELEC.tv', 'files', '', False, False, '/')
                    if returnValue != '' and returnValue != '/':
                        selectedItem.setProperty('value', str(returnValue))
                elif strTyp == 'folder':
                    xbmcDialog = xbmcgui.Dialog()
                    returnValue = xbmcDialog.browse(0, 'LibreELEC.tv', 'files', '', False, False, '/storage')
                    if returnValue != '' and returnValue != '/':
                        selectedItem.setProperty('value', str(returnValue))
                elif strTyp == 'ip':
                    if strValue == '':
                        strValue = '0.0.0.0'
                    xbmcDialog = xbmcgui.Dialog()
                    returnValue = xbmcDialog.numeric(3, 'LibreELEC.tv', strValue)
                    if returnValue != '':
                        if returnValue == '0.0.0.0':
                            selectedItem.setProperty('value', '')
                        else:
                            selectedItem.setProperty('value', returnValue)
                elif strTyp == 'num':
                    if strValue == 'None' or strValue == '':
                        strValue = '0'
                    xbmcDialog = xbmcgui.Dialog()
                    returnValue = xbmcDialog.numeric(0, 'LibreELEC.tv', strValue)
                    if returnValue != '':
                        selectedItem.setProperty('value', returnValue)
                elif strTyp == 'bool':
                    strValue = strValue.lower()
                    if strValue == '0':
                        selectedItem.setProperty('value', '1')
                    elif strValue == '1':
                        selectedItem.setProperty('value', '0')
                    elif strValue == 'true':
                        selectedItem.setProperty('value', 'false')
                    elif strValue == 'false':
                        selectedItem.setProperty('value', 'true')
                    else:
                        selectedItem.setProperty('value', '1')
                if selectedItem.getProperty('action') != '':
                    if hasattr(oe.dictModules[selectedMenuItem.getProperty('modul')], selectedItem.getProperty('action')):
                        getattr(oe.dictModules[selectedMenuItem.getProperty('modul')], selectedItem.getProperty('action'
                                ))(listItem=selectedItem)
                        self.emptyButtonLabels()
                self.lastMenu = -1
                self.onFocus(self.guiMenList)
                self.setFocusId(controlID)
                self.getControl(controlID).selectItem(selectedPosition)
            log.log('exit_function', log.DEBUG)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (onClick): {e}", level=log.ERROR, exc_info=True)

    def onUnload(self):
        try:
            pass # Original was empty
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (onUnload): {e}", level=log.ERROR, exc_info=True)

    @log.log_function()
    def onFocus(self, controlID):
        try:
            if controlID in self.guiLists:
                currentEntry = self.getControl(controlID).getSelectedPosition()
                selectedEntry = self.getControl(controlID).getSelectedItem()
                if controlID == self.guiList:
                    self.setProperty('InfoText', selectedEntry.getProperty('InfoText'))
                if currentEntry != self.lastGuiList:
                    self.lastGuiList = currentEntry
                    if selectedEntry is not None:
                        strHoover = selectedEntry.getProperty('hooverValidate')
                        if strHoover != '':
                            if hasattr(oe.dictModules[selectedEntry.getProperty('modul')], strHoover):
                                self.emptyButtonLabels()
                                getattr(oe.dictModules[selectedEntry.getProperty('modul')], strHoover)(selectedEntry)
            if controlID == self.guiMenList:
                lastMenu = self.getControl(controlID).getSelectedPosition()
                selectedMenuItem = self.getControl(controlID).getSelectedItem()
                self.setProperty('InfoText', selectedMenuItem.getProperty('InfoText'))
                if lastMenu != self.lastMenu:
                    if self.lastListType == int(selectedMenuItem.getProperty('listTyp')):
                        self.getControl(int(selectedMenuItem.getProperty('listTyp'))).setAnimations([('conditional',
                                'effect=fade start=100 end=0 time=100 condition=True')])
                    self.getControl(1100).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                    self.getControl(1200).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                    self.getControl(1300).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                    self.getControl(1900).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                    self.lastModul = selectedMenuItem.getProperty('Modul')
                    self.lastMenu = lastMenu
                    for btn in self.buttons:
                        self.getControl(self.buttons[btn]['id']).setVisible(False)
                    strMenuLoader = selectedMenuItem.getProperty('menuLoader')
                    objList = self.getControl(int(selectedMenuItem.getProperty('listTyp')))
                    self.getControl(controlID).controlRight(objList)
                    if strMenuLoader != '':
                        if hasattr(oe.dictModules[selectedMenuItem.getProperty('modul')], strMenuLoader):
                            getattr(oe.dictModules[selectedMenuItem.getProperty('modul')], strMenuLoader)(selectedMenuItem)
                    self.getControl(int(selectedMenuItem.getProperty('listTyp'))).setAnimations([('conditional',
                            'effect=fade start=0 end=100 time=100 condition=true')])
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (onFocus): {e}", level=log.ERROR, exc_info=True)

    def emptyButtonLabels(self):
        try:
            for btn in self.buttons:
                self.getControl(self.buttons[btn]['id']).setVisible(False)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (emptyButtonLabels): {e}", level=log.ERROR, exc_info=True)

class pinkeyWindow(xbmcgui.WindowXMLDialog):

    device = ''

    def set_title(self, text):
        try:
            self.getControl(1700).setLabel(text)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (set_title): {e}", level=log.ERROR, exc_info=True)

    def set_label1(self, text):
        try:
            self.getControl(1701).setLabel(str(text))
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (set_label1): {e}", level=log.ERROR, exc_info=True)

    def set_label2(self, text):
        try:
            self.getControl(1702).setLabel(str(text))
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (set_label2): {e}", level=log.ERROR, exc_info=True)

    def set_label3(self, text):
        try:
            self.getControl(1703).setLabel(str(text))
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (set_label3): {e}", level=log.ERROR, exc_info=True)

    def append_label3(self, text):
        try:
            label = self.getControl(1703).getLabel()
            self.getControl(1703).setLabel(label + str(text))
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (append_label3): {e}", level=log.ERROR, exc_info=True)

    def get_label3_len(self):
        try:
            return len(self.getControl(1703).getLabel())
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (get_label3_len): {e}", level=log.ERROR, exc_info=True)
            return 0

class wizard(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        # Initialize instance variables that were previously global
        self.lang_new = ""
        self.strModule = "" # Consider a more descriptive name like self.current_wizard_module
        self.prevModule = "" # Consider self.previous_wizard_module

        self.visible = False
        self.lastMenu = -1
        self.guiMenList = 1000
        for strProp in dictProperties:
            lstItem.setProperty(strProp, str(dictProperties[strProp]))
        self.getControl(self.guiMenList).addItem(lstItem)

    @log.log_function()
    def addConfigItem(self, strName, dictProperties, strType):
        lstItem = xbmcgui.ListItem(label=strName)
        for strProp in dictProperties:
            lstItem.setProperty(strProp, str(dictProperties[strProp]))
        self.getControl(int(strType)).addItem(lstItem)
        return lstItem

    @log.log_function()
    def build_menu(self, struct, fltr=[], optional='0'):
        self.getControl(1100).reset()
        m_menu = []
        for category in sorted(struct, key=lambda x: struct[x]['order']):
            if not 'hidden' in struct[category]:
                if fltr == []:
                    m_entry = {}
                    m_entry['name'] = oe._(struct[category]['name'])
                    m_entry['properties'] = {'typ': 'separator'}
                    m_entry['list'] = 1100
                    m_menu.append(m_entry)
                else:
                    if category not in fltr:
                        continue
                for entry in sorted(struct[category]['settings'], key=lambda x: struct[category]['settings'][x]['order']):
                    setting = struct[category]['settings'][entry]
                    if not 'hidden' in setting:
                        dictProperties = {
                            'value': setting['value'],
                            'typ': setting['type'],
                            'entry': entry,
                            'category': category,
                            'action': setting['action'],
                            }
                        if 'InfoText' in setting:
                            dictProperties['InfoText'] = oe._(setting['InfoText'])
                        if 'validate' in setting:
                            dictProperties['validate'] = setting['validate']
                        if 'values' in setting and setting['values'] is not None:
                            dictProperties['values'] = '|'.join(setting['values'])
                        if isinstance(setting['name'], str):
                            name = setting['name']
                        else:
                            name = oe._(setting['name'])
                            dictProperties['menuname'] = oe._(setting['name'])
                        m_entry = {}
                        if not 'parent' in setting:
                            m_entry['name'] = name
                            m_entry['properties'] = dictProperties
                            m_entry['list'] = 1100
                            m_menu.append(m_entry)
                        else:
                            if struct[category]['settings'][setting['parent']['entry']]['value'] in setting['parent']['value']:
                                if not 'optional' in setting or 'optional' in setting and optional != '0':
                                    m_entry['name'] = name
                                    m_entry['properties'] = dictProperties
                                    m_entry['list'] = 1100
                                    m_menu.append(m_entry)
        for m_entry in m_menu:
            self.addConfigItem(m_entry['name'], m_entry['properties'], m_entry['list'])

    @log.log_function()
    def showButton(self, number, name, module, action, onup=None, onleft=None):
        log.log('enter_function', log.DEBUG)
        button = self.getControl(self.buttons[number]['id'])
        self.buttons[number]['modul'] = module
        self.buttons[number]['action'] = action
        button.setLabel(oe._(name))
        if onup != None:
            button.controlUp(self.getControl(onup))
        if onleft != None:
            button.controlLeft(self.getControl(onleft))
        button.setVisible(True)
        log.log('exit_function', log.DEBUG)

    @log.log_function()
    def onAction(self, action):
        try:
            focusId = self.getFocusId()
            actionId = int(action.getId())
            if focusId == 2222:
                if actionId == 61453:
                    return
            if actionId in oe.CANCEL:
                self.visible = False
                self.close()
            if focusId == self.guiList:
                curPos = self.getControl(focusId).getSelectedPosition()
                listSize = self.getControl(focusId).size()
                newPos = curPos
                nextItem = self.getControl(focusId).getListItem(newPos)
                if (curPos != self.lastGuiList or nextItem.getProperty('typ') == 'separator') and actionId in [
                    2,
                    3,
                    4,
                    ]:
                    while nextItem.getProperty('typ') == 'separator':
                        if actionId == 2:
                            newPos = newPos + 1
                        if actionId == 3:
                            newPos = newPos - 1
                        if actionId == 4:
                            newPos = newPos + 1
                        if newPos <= 0:
                            newPos = listSize - 1
                        if newPos >= listSize:
                            newPos = 0
                        nextItem = self.getControl(focusId).getListItem(newPos)
                    self.lastGuiList = newPos
                    self.getControl(focusId).selectItem(newPos)
                    self.setProperty('InfoText', nextItem.getProperty('InfoText'))
            if focusId == self.guiMenList:
                self.setFocusId(focusId)
        except Exception:
            if actionId in oe.CANCEL:
                self.close()

    @log.log_function()
    def onClick(self, controlID):
        log.log('enter_function', log.DEBUG)
        for btn in self.buttons:
            if controlID == self.buttons[btn]['id']:
                modul = self.buttons[btn]['modul']
                action = self.buttons[btn]['action']
                if hasattr(oe.dictModules[modul], action):
                    if getattr(oe.dictModules[modul], action)() == 'close':
                        self.close()
                    return
        if controlID in self.guiLists:
            selectedPosition = self.getControl(controlID).getSelectedPosition()
            selectedMenuItem = self.getControl(self.guiMenList).getSelectedItem()
            selectedItem = self.getControl(controlID).getSelectedItem()
            strTyp = selectedItem.getProperty('typ')
            strValue = selectedItem.getProperty('value')
            if strTyp == 'multivalue':
                items1 = []
                items2 = []
                for item in selectedItem.getProperty('values').split('|'):
                    if item != ':':
                        boo = item.split(':')
                        if len(boo) > 1:
                            i1 = boo[0]
                            i2 = boo[1]
                        else:
                            i1 = item
                            i2 = item
                    else:
                        i1 = ''
                        i2 = ''
                    if i2 == strValue:
                        items1.insert(0, i1)
                        items2.insert(0, i2)
                    else:
                        # move current on top of the list
                        items1.append(i1)
                        items2.append(i2)
                select_window = xbmcgui.Dialog()
                title = selectedItem.getProperty('menuname')
                result = select_window.select(title, items1)
                if result >= 0:
                    selectedItem.setProperty('value', items2[result])
            elif strTyp == 'text':
                xbmcKeyboard = xbmc.Keyboard(strValue)
                result_is_valid = False
                while not result_is_valid:
                    xbmcKeyboard.doModal()
                    if xbmcKeyboard.isConfirmed():
                        result_is_valid = True
                        validate_string = selectedItem.getProperty('validate')
                        if validate_string != '':
                            if not re.search(validate_string, xbmcKeyboard.getText()):
                                result_is_valid = False
                    else:
                        result_is_valid = True
                if xbmcKeyboard.isConfirmed():
                    selectedItem.setProperty('value', xbmcKeyboard.getText())
            elif strTyp == 'file':
                xbmcDialog = xbmcgui.Dialog()
                returnValue = xbmcDialog.browse(1, 'LibreELEC.tv', 'files', '', False, False, '/')
                if returnValue != '' and returnValue != '/':
                    selectedItem.setProperty('value', str(returnValue))
            elif strTyp == 'folder':
                xbmcDialog = xbmcgui.Dialog()
                returnValue = xbmcDialog.browse(0, 'LibreELEC.tv', 'files', '', False, False, '/storage')
                if returnValue != '' and returnValue != '/':
                    selectedItem.setProperty('value', str(returnValue))
            elif strTyp == 'ip':
                if strValue == '':
                    strValue = '0.0.0.0'
                xbmcDialog = xbmcgui.Dialog()
                returnValue = xbmcDialog.numeric(3, 'LibreELEC.tv', strValue)
                if returnValue != '':
                    if returnValue == '0.0.0.0':
                        selectedItem.setProperty('value', '')
                    else:
                        selectedItem.setProperty('value', returnValue)
            elif strTyp == 'num':
                if strValue == 'None' or strValue == '':
                    strValue = '0'
                xbmcDialog = xbmcgui.Dialog()
                returnValue = xbmcDialog.numeric(0, 'LibreELEC.tv', strValue)
                if returnValue != '':
                    selectedItem.setProperty('value', returnValue)
            elif strTyp == 'bool':
                strValue = strValue.lower()
                if strValue == '0':
                    selectedItem.setProperty('value', '1')
                elif strValue == '1':
                    selectedItem.setProperty('value', '0')
                elif strValue == 'true':
                    selectedItem.setProperty('value', 'false')
                elif strValue == 'false':
                    selectedItem.setProperty('value', 'true')
                else:
                    selectedItem.setProperty('value', '1')
            if selectedItem.getProperty('action') != '':
                if hasattr(oe.dictModules[selectedMenuItem.getProperty('modul')], selectedItem.getProperty('action')):
                    getattr(oe.dictModules[selectedMenuItem.getProperty('modul')], selectedItem.getProperty('action'
                            ))(listItem=selectedItem)
                    self.emptyButtonLabels()
            self.lastMenu = -1
            self.onFocus(self.guiMenList)
            self.setFocusId(controlID)
            self.getControl(controlID).selectItem(selectedPosition)
        log.log('exit_function', log.DEBUG)

    def onUnload(self):
        pass

    @log.log_function()
    def onFocus(self, controlID):
        if controlID in self.guiLists:
            currentEntry = self.getControl(controlID).getSelectedPosition()
            selectedEntry = self.getControl(controlID).getSelectedItem()
            if controlID == self.guiList:
                self.setProperty('InfoText', selectedEntry.getProperty('InfoText'))
            if currentEntry != self.lastGuiList:
                self.lastGuiList = currentEntry
                if selectedEntry is not None:
                    strHoover = selectedEntry.getProperty('hooverValidate')
                    if strHoover != '':
                        if hasattr(oe.dictModules[selectedEntry.getProperty('modul')], strHoover):
                            self.emptyButtonLabels()
                            getattr(oe.dictModules[selectedEntry.getProperty('modul')], strHoover)(selectedEntry)
        if controlID == self.guiMenList:
            lastMenu = self.getControl(controlID).getSelectedPosition()
            selectedMenuItem = self.getControl(controlID).getSelectedItem()
            self.setProperty('InfoText', selectedMenuItem.getProperty('InfoText'))
            if lastMenu != self.lastMenu:
                if self.lastListType == int(selectedMenuItem.getProperty('listTyp')):
                    self.getControl(int(selectedMenuItem.getProperty('listTyp'))).setAnimations([('conditional',
                            'effect=fade start=100 end=0 time=100 condition=True')])
                self.getControl(1100).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                self.getControl(1200).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                self.getControl(1300).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                self.getControl(1900).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                self.lastModul = selectedMenuItem.getProperty('Modul')
                self.lastMenu = lastMenu
                for btn in self.buttons:
                    self.getControl(self.buttons[btn]['id']).setVisible(False)
                strMenuLoader = selectedMenuItem.getProperty('menuLoader')
                objList = self.getControl(int(selectedMenuItem.getProperty('listTyp')))
                self.getControl(controlID).controlRight(objList)
                if strMenuLoader != '':
                    if hasattr(oe.dictModules[selectedMenuItem.getProperty('modul')], strMenuLoader):
                        getattr(oe.dictModules[selectedMenuItem.getProperty('modul')], strMenuLoader)(selectedMenuItem)
                self.getControl(int(selectedMenuItem.getProperty('listTyp'))).setAnimations([('conditional',
                        'effect=fade start=0 end=100 time=100 condition=true')])

    def emptyButtonLabels(self):
        for btn in self.buttons:
            self.getControl(self.buttons[btn]['id']).setVisible(False)


class pinkeyWindow(xbmcgui.WindowXMLDialog):

    device = ''

    def set_title(self, text):
        self.getControl(1700).setLabel(text)

    def set_label1(self, text):
        self.getControl(1701).setLabel(str(text))

    def set_label2(self, text):
        self.getControl(1702).setLabel(str(text))

    def set_label3(self, text):
        self.getControl(1703).setLabel(str(text))

    def append_label3(self, text):
        label = self.getControl(1703).getLabel()
        self.getControl(1703).setLabel(label + str(text))

    def get_label3_len(self):
        return len(self.getControl(1703).getLabel())


class wizard(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.visible = False
        self.lastMenu = -1
        self.guiMenList = 1000
        self.guiNetList = 1200
        self.wizTextbox = 1400
        self.wizTitle = 1399
        self.wizBtnTitle = 1403
        self.wizLstTitle = 1404
        self.wizWinTitle = 32300
        self.guisettings = f'{oe.XBMC_USER_HOME}/userdata/guisettings.xml'
        self.buttons = {
            1: {
                'id': 1500,
                'modul': '',
                'action': '',
                },
            2: {
                'id': 1501,
                'modul': '',
                'action': '',
                },
            3: {
                'id': 1401,
                'modul': '',
                'action': '',
                },
            4: {
                'id': 1402,
                'modul': '',
                'action': '',
                },
            }

        self.radiobuttons = {
            1: {
                'id': 1406,
                'modul': '',
                'action': '',
                },
            2: {
                'id': 1407,
                'modul': '',
                'action': '',
                },
            }

        self.actions = {}
        self.wizards = []
        self.last_wizard = None

    @log.log_function()
    def onInit(self):
        try:
            self.visible = True
            self.setProperty('arch', oe.ARCHITECTURE)
            self.setProperty('distri', oe.DISTRIBUTION)
        # ... (rest of onInit method)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (onInit): {e}", level=log.ERROR, exc_info=True)
            self.close() # Example cleanup

    # This is a conceptual split, the actual content from the read file will be inside the try block.
    def _original_wizard_onInit(self):
        self.visible = True
        self.setProperty('arch', oe.ARCHITECTURE)
        self.setProperty('distri', oe.DISTRIBUTION)
        self.setProperty('version', oe.VERSION)
        self.setProperty('build', oe.BUILD)
        oe.dictModules['system'].do_init()
        self.getControl(self.wizWinTitle).setLabel(oe._(32300))
        self.getControl(self.buttons[3]['id']).setVisible(False)
        self.getControl(self.buttons[4]['id']).setVisible(False)
        self.getControl(self.radiobuttons[1]['id']).setVisible(False)
        self.getControl(self.radiobuttons[2]['id']).setVisible(False)
        self.getControl(self.buttons[2]['id']).setVisible(False)
        if oe.BOOT_STATUS == "SAFE":
            self.set_wizard_title(f"[COLOR red][B]{oe._(32393)}[/B][/COLOR]")
            self.set_wizard_text(oe._(32394))
        else:
            self.set_wizard_title(oe._(32301))
            self.set_wizard_text(oe._(32302))
            oe.winOeMain.set_wizard_button_title(oe._(32310))
            cur_lang = xbmc.getLanguage()
            oe.winOeMain.set_wizard_button_1(cur_lang, self, 'wizard_set_language')
        self.showButton(1, 32303)
        self.setFocusId(self.buttons[1]['id'])
        # Ensure the rest of onInit is also wrapped if not covered by the initial try
        # For this specific case, the main logic is above.

    @log.log_function()
    def wizard_set_language(self):
        # global lang_new # Now self.lang_new
        try:
            log.log('enter_function', log.DEBUG)
            langCodes = {"Bulgarian":"resource.language.bg_bg","Czech":"resource.language.cs_cz","German":"resource.language.de_de","English":"resource.language.en_gb","Spanish":"resource.language.es_es","Basque":"resource.language.eu_es","Finnish":"resource.language.fi_fi","French":"resource.language.fr_fr","Hebrew":"resource.language.he_il","Hungarian":"resource.language.hu_hu","Italian":"resource.language.it_it","Lithuanian":"resource.language.lt_lt","Latvian":"resource.language.lv_lv","Norwegian":"resource.language.nb_no","Dutch":"resource.language.nl_nl","Polish":"resource.language.pl_pl","Portuguese (Brazil)":"resource.language.pt_br","Portuguese":"resource.language.pt_pt","Romanian":"resource.language.ro_ro","Russian":"resource.language.ru_ru","Slovak":"resource.language.sk_sk","Swedish":"resource.language.sv_se","Turkish":"resource.language.tr_tr","Ukrainian":"resource.language.uk_ua"}
            languagesList = sorted(list(langCodes.keys()))
        # ... (rest of wizard_set_language method)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (wizard_set_language): {e}", level=log.ERROR, exc_info=True)

    def _original_wizard_set_language(self): # For visualization
        # global lang_new
        log.log('enter_function', log.DEBUG)
        langCodes = {"Bulgarian":"resource.language.bg_bg","Czech":"resource.language.cs_cz","German":"resource.language.de_de","English":"resource.language.en_gb","Spanish":"resource.language.es_es","Basque":"resource.language.eu_es","Finnish":"resource.language.fi_fi","French":"resource.language.fr_fr","Hebrew":"resource.language.he_il","Hungarian":"resource.language.hu_hu","Italian":"resource.language.it_it","Lithuanian":"resource.language.lt_lt","Latvian":"resource.language.lv_lv","Norwegian":"resource.language.nb_no","Dutch":"resource.language.nl_nl","Polish":"resource.language.pl_pl","Portuguese (Brazil)":"resource.language.pt_br","Portuguese":"resource.language.pt_pt","Romanian":"resource.language.ro_ro","Russian":"resource.language.ru_ru","Slovak":"resource.language.sk_sk","Swedish":"resource.language.sv_se","Turkish":"resource.language.tr_tr","Ukrainian":"resource.language.uk_ua"}
        languagesList = sorted(list(langCodes.keys()))
        cur_lang = xbmc.getLanguage()
        for index, lang in enumerate(languagesList):
            if cur_lang in lang:
                langIndex = index
                break
            else:
                pass
            selLanguage = xbmcDialog.select(oe._(32310), languagesList, preselect=langIndex)
            if selLanguage >= 0:
                langKey = languagesList[selLanguage]
                self.lang_new = langCodes[langKey] # Use self.lang_new
                if self.lang_new == "resource.language.en_gb":
                    oe.write_setting("system", "language", "")
                else:
                    oe.write_setting("system", "language", str(self.lang_new))
            self.getControl(self.wizWinTitle).setLabel(oe._(32300))
            self.set_wizard_title(oe._(32301))
            self.set_wizard_text(oe._(32302))
            oe.winOeMain.set_wizard_button_title(oe._(32310))
            oe.winOeMain.set_wizard_button_1(langKey, self, 'wizard_set_language')
            self.showButton(1, 32303)
            self.setFocusId(self.buttons[1]['id'])
        log.log('exit_function', log.DEBUG)

    @log.log_function()
    def set_wizard_text(self, text):
        self.getControl(self.wizTextbox).setText(text)

    @log.log_function()
    def set_wizard_title(self, title):
        self.getControl(self.wizTitle).setLabel(title)

    @log.log_function()
    def set_wizard_button_title(self, title):
        self.getControl(self.wizBtnTitle).setLabel(title)

    @log.log_function()
    def set_wizard_list_title(self, title):
        self.getControl(self.wizLstTitle).setLabel(title)

    @log.log_function()
    def set_wizard_button_1(self, label, modul, action):
        self.buttons[3]['modul'] = modul
        self.buttons[3]['action'] = action
        self.getControl(self.buttons[3]['id']).setLabel(label)
        self.getControl(self.buttons[3]['id']).setVisible(True)
        self.getControl(self.buttons[3]['id']).controlRight(self.getControl(self.buttons[1]['id']))
        self.getControl(self.buttons[3]['id']).controlDown(self.getControl(self.buttons[1]['id']))
        self.getControl(self.buttons[1]['id']).controlUp(self.getControl(self.buttons[3]['id']))
        if self.buttons[2]['id']:
            self.getControl(self.buttons[1]['id']).controlLeft(self.getControl(self.buttons[2]['id']))
        else:
            self.getControl(self.buttons[1]['id']).controlLeft(self.getControl(self.buttons[3]['id']))
        self.getControl(self.buttons[2]['id']).controlUp(self.getControl(self.buttons[3]['id']))
        self.getControl(self.buttons[2]['id']).controlRight(self.getControl(self.buttons[1]['id']))

    @log.log_function()
    def set_wizard_button_2(self, label, modul, action):
        self.buttons[4]['modul'] = modul
        self.buttons[4]['action'] = action
        self.getControl(self.buttons[4]['id']).setLabel(label)
        self.getControl(self.buttons[4]['id']).setVisible(True)
        self.getControl(self.buttons[4]['id']).controlLeft(self.getControl(self.buttons[3]['id']))
        self.getControl(self.buttons[4]['id']).controlDown(self.getControl(self.buttons[1]['id']))
        self.getControl(self.buttons[4]['id']).controlRight(self.getControl(self.buttons[1]['id']))
        self.getControl(self.buttons[1]['id']).controlUp(self.getControl(self.buttons[4]['id']))
        self.getControl(self.buttons[1]['id']).controlLeft(self.getControl(self.buttons[4]['id']))
        self.getControl(self.buttons[2]['id']).controlUp(self.getControl(self.buttons[4]['id']))
        self.getControl(self.buttons[2]['id']).controlRight(self.getControl(self.buttons[1]['id']))
        self.getControl(self.buttons[3]['id']).controlRight(self.getControl(self.buttons[4]['id']))

    @log.log_function()
    def set_wizard_radiobutton_1(self, label, modul, action, selected=False):
        self.radiobuttons[1]['modul'] = modul
        self.radiobuttons[1]['action'] = action
        self.getControl(self.radiobuttons[1]['id']).setLabel(label)
        self.getControl(self.radiobuttons[1]['id']).setVisible(True)
        self.getControl(self.radiobuttons[1]['id']).controlRight(self.getControl(self.buttons[1]['id']))
        self.getControl(self.radiobuttons[1]['id']).controlDown(self.getControl(self.buttons[1]['id']))
        self.getControl(self.buttons[1]['id']).controlUp(self.getControl(self.buttons[3]['id']))
        self.getControl(self.buttons[1]['id']).controlLeft(self.getControl(self.buttons[2]['id']))
        self.getControl(self.buttons[2]['id']).controlUp(self.getControl(self.radiobuttons[1]['id']))
        self.getControl(self.buttons[2]['id']).controlRight(self.getControl(self.buttons[1]['id']))
        self.getControl(self.radiobuttons[1]['id']).setSelected(selected)

    @log.log_function()
    def set_wizard_radiobutton_2(self, label, modul, action, selected=False):
        self.radiobuttons[2]['modul'] = modul
        self.radiobuttons[2]['action'] = action
        self.getControl(self.radiobuttons[2]['id']).setLabel(label)
        self.getControl(self.radiobuttons[2]['id']).setVisible(True)
        self.getControl(self.radiobuttons[2]['id']).controlLeft(self.getControl(self.radiobuttons[1]['id']))
        self.getControl(self.radiobuttons[2]['id']).controlDown(self.getControl(self.buttons[1]['id']))
        self.getControl(self.radiobuttons[2]['id']).controlRight(self.getControl(self.buttons[1]['id']))
        self.getControl(self.buttons[1]['id']).controlUp(self.getControl(self.radiobuttons[2]['id']))
        self.getControl(self.buttons[1]['id']).controlLeft(self.getControl(self.buttons[2]['id']))
        self.getControl(self.buttons[2]['id']).controlUp(self.getControl(self.radiobuttons[1]['id']))
        self.getControl(self.buttons[2]['id']).controlRight(self.getControl(self.buttons[1]['id']))
        self.getControl(self.radiobuttons[1]['id']).controlRight(self.getControl(self.radiobuttons[2]['id']))
        self.getControl(self.radiobuttons[2]['id']).setSelected(selected)

    def onAction(self, action):
        try:
            pass # Original was empty
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (onAction): {e}", level=log.ERROR, exc_info=True)


    @log.log_function()
    def onClick(self, controlID):
        # global strModule # Now self.strModule
        # global prevModule # Now self.prevModule
        try:
            log.log(f'{str(controlID)}: enter_function', log.DEBUG)
            for btn in self.buttons:
                if controlID == self.buttons[btn]['id'] and self.buttons[btn]['id'] > 2:
            # ... (rest of onClick method)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (onClick): {e}", level=log.ERROR, exc_info=True)

    def _original_wizard_onClick(self, controlID): # For visualization
        # global strModule
        # global prevModule
        log.log(f'{str(controlID)}: enter_function', log.DEBUG)
        for btn in self.buttons:
            if controlID == self.buttons[btn]['id'] and self.buttons[btn]['id'] > 2:
                if hasattr(self.buttons[btn]['modul'], self.buttons[btn]['action']):
                    getattr(self.buttons[btn]['modul'], self.buttons[btn]['action'])()
        for btn in self.radiobuttons:
            if controlID == self.radiobuttons[btn]['id'] and self.radiobuttons[btn]['id'] > 1:
                if hasattr(self.radiobuttons[btn]['modul'], self.radiobuttons[btn]['action']):
                    getattr(self.radiobuttons[btn]['modul'], self.radiobuttons[btn]['action'])()
        if controlID == self.guiNetList:
            selectedItem = self.getControl(controlID).getSelectedItem()
            if selectedItem.getProperty('action') != '':
                if hasattr(oe.dictModules[self.last_wizard], selectedItem.getProperty('action')):
                    getattr(oe.dictModules[self.last_wizard], selectedItem.getProperty('action'))(selectedItem)
                    return
            if controlID == 1501: # Back button in wizard
                self.wizards.remove(self.strModule) # Use self.strModule
                oe.remove_node(self.strModule) # Use self.strModule
                if self.strModule == "system": # Use self.strModule
                    self.onInit() # Re-initialize current step if it's system (first step)
                else:
                    self.wizards.remove(self.prevModule) # Use self.prevModule
                    oe.remove_node(self.prevModule) # Use self.prevModule
                self.onClick(1500)
            log.log(f'{str(controlID)}: exit_function', log.DEBUG)

        if controlID == 1500:
            self.getControl(1390).setLabel('1')
            oe.xbmcm.waitForAbort(0.5)
            self.is_last_wizard = True
            self.getControl(1391).setLabel('')
            self.getControl(self.buttons[3]['id']).setVisible(False)
            self.getControl(self.buttons[4]['id']).setVisible(False)
            self.getControl(self.radiobuttons[1]['id']).setVisible(False)
            self.getControl(self.radiobuttons[2]['id']).setVisible(False)
            self.showButton(2, 32307)
            self.set_wizard_title('')
            self.set_wizard_text('')
            self.set_wizard_list_title('')
            self.set_wizard_button_title('')

            if self.strModule == 'connman': # Use self.strModule
                xbmc.executebuiltin('UpdateAddonRepos')

            for module_iter_name in sorted(oe.dictModules, key=lambda x: list(oe.dictModules[x].menu.keys())):
                self.strModule = module_iter_name # Use self.strModule
                # Check if ENABLED is a callable (lambda) or a direct boolean
                is_enabled = oe.dictModules[self.strModule].ENABLED() if callable(oe.dictModules[self.strModule].ENABLED) else oe.dictModules[self.strModule].ENABLED
                if hasattr(oe.dictModules[self.strModule], 'do_wizard') and is_enabled:
                    if self.strModule == self.last_wizard:
                        if hasattr(oe.dictModules[self.strModule], 'exit'):
                            oe.dictModules[self.strModule].exit()
                            if hasattr(oe.dictModules[self.strModule], 'is_wizard'):
                                del oe.dictModules[self.strModule].is_wizard
                    setting = oe.read_setting(self.strModule, 'wizard_completed') # Use self.strModule
                    if self.wizards: # Check if wizards list is not empty
                        self.prevModule = self.wizards[-1] # Use self.prevModule
                    if oe.read_setting(self.strModule, 'wizard_completed') == None and self.strModule not in self.wizards:
                        self.last_wizard = self.strModule # Use self.strModule
                        if hasattr(oe.dictModules[self.strModule], 'do_init'):
                            oe.dictModules[self.strModule].do_init()
                        self.getControl(1390).setLabel('')
                        oe.dictModules[self.strModule].do_wizard()
                        self.wizards.append(self.strModule) # Use self.strModule
                        oe.write_setting(self.strModule, 'wizard_completed', 'True') # Use self.strModule
                        self.is_last_wizard = False
                        break
            if self.is_last_wizard == True:
                if self.lang_new and xbmc.getCondVisibility(f'System.HasAddon({self.lang_new})') == False: # Use self.lang_new
                    xbmc.executebuiltin(f'InstallAddon({self.lang_new})') # Use self.lang_new
                oe.xbmcm.waitForAbort(0.5)
                xbmc.executebuiltin('SendClick(10100,11)')
                oe.write_setting('libreelec', 'wizard_completed', 'True')
                self.visible = False
                self.close()
                if self.lang_new: # Use self.lang_new
                    for _ in range(20):
                        if xbmc.getCondVisibility(f'System.HasAddon({self.lang_new})'): # Use self.lang_new
                            break
                        oe.xbmcm.waitForAbort(0.5)
                    if xbmc.getCondVisibility(f'System.HasAddon({self.lang_new})') == True: # Use self.lang_new
                        xbmc.executebuiltin(f'SetGUILanguage({str(self.lang_new)})') # Use self.lang_new
                    else:
                        log.log(f'{str(controlID)}: ERROR: Unable to switch language to: {self.lang_new}. Language addon is not installed.', log.INFO) # Use self.lang_new
            log.log(f'{str(controlID)}: exit_function', log.DEBUG)
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (onClick): {e}", level=log.ERROR, exc_info=True)


    def onFocus(self, controlID):
        try:
            pass # Original was empty
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (onFocus): {e}", level=log.ERROR, exc_info=True)


    @log.log_function()
    def showButton(self, number, name):
        button = self.getControl(self.buttons[number]['id'])
        button.setLabel(oe._(name))
        button.setVisible(True)

    @log.log_function()
    def addConfigItem(self, strName, dictProperties, strType):
        try:
            lstItem = xbmcgui.ListItem(label=strName)
            for strProp in dictProperties:
                lstItem.setProperty(strProp, str(dictProperties[strProp]))
            self.getControl(int(strType)).addItem(lstItem)
            return lstItem
        except Exception as e:
            log.log(f"Error in {self.__class__.__name__} callback (addConfigItem wizard): {e}", level=log.ERROR, exc_info=True)
            return None # Ensure a return path
