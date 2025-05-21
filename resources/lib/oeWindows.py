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


# Constants for control IDs in mainWindow
MAIN_CONTROL_MENU_LIST = 1000
MAIN_CONTROL_SETTINGS_LIST = 1100
MAIN_CONTROL_NETWORK_LIST = 1200
MAIN_CONTROL_BLUETOOTH_LIST = 1300
MAIN_CONTROL_OTHER_LIST = 1900
MAIN_BUTTON_ACTION_1 = 1500  # Renamed from MAIN_BUTTON_SAVE_SETTINGS for generic use
MAIN_BUTTON_ACTION_2 = 1501  # Renamed from MAIN_BUTTON_CANCEL for generic use
MAIN_SPECIFIC_FOCUS_ID_2222 = 2222 # As used in onAction

# Constants for control IDs in pinkeyWindow
PINKEY_LABEL_TITLE = 1700
PINKEY_LABEL_LINE1 = 1701
PINKEY_LABEL_LINE2 = 1702
PINKEY_LABEL_PIN_DISPLAY = 1703
# PINKEY_PROGRESS_BAR = 1704 # This ID was mentioned but not found in the provided oeWindows.py. Will omit.

# Constants for control IDs in wizard
# Assuming WIZARD_CONTROL_MENU_LIST and WIZARD_CONTROL_NETWORK_LIST are distinct from MAIN_ ones
# If they refer to the same conceptual controls in a shared/similar XML part, MAIN_ constants could be used.
# For now, defining them separately as per instruction's lean towards distinct contexts.
WIZARD_CONTROL_MENU_LIST = 1000
WIZARD_CONTROL_NETWORK_LIST = 1200 # Used in onClick for self.guiNetList
WIZARD_TEXTBOX = 1400
WIZARD_LABEL_TITLE = 1399
WIZARD_LABEL_BUTTON_AREA_TITLE = 1403
WIZARD_LABEL_LIST_AREA_TITLE = 1404
# WIZARD_LABEL_WINDOW_TITLE = 32300 # This is a string ID for localization, not a numeric control ID.
WIZARD_BUTTON_NEXT_FINISH = 1500 # buttons[1]['id'] - Next/Finish
WIZARD_BUTTON_SKIP_CANCEL = 1501 # buttons[2]['id'] - Skip/Cancel
WIZARD_BUTTON_CUSTOM_1 = 1401   # buttons[3]['id']
WIZARD_BUTTON_CUSTOM_2 = 1402   # buttons[4]['id']
WIZARD_RADIOBUTTON_1 = 1406
WIZARD_RADIOBUTTON_2 = 1407
WIZARD_PROGRESS_INDICATOR_LABEL = 1390
WIZARD_AUX_LABEL = 1391


xbmcDialog = xbmcgui.Dialog()

__scriptid__ = 'service.libreelec.settings'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
__cwd__ = __addon__.getAddonInfo('path')

lang_new = ""
strModule = ""
prevModule = ""

class mainWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.visible = False
        self.lastMenu = -1
        self.lastEntry = -1
        self.guiMenList = MAIN_CONTROL_MENU_LIST
        self.guiList = MAIN_CONTROL_SETTINGS_LIST
        self.guiNetList = MAIN_CONTROL_NETWORK_LIST
        self.guiBtList = MAIN_CONTROL_BLUETOOTH_LIST
        self.guiOther = MAIN_CONTROL_OTHER_LIST
        self.guiLists = [
            MAIN_CONTROL_MENU_LIST,
            MAIN_CONTROL_SETTINGS_LIST,
            MAIN_CONTROL_NETWORK_LIST,
            MAIN_CONTROL_BLUETOOTH_LIST,
            # MAIN_CONTROL_OTHER_LIST is not typically in guiLists for direct item manipulation
            ]
        self.buttons = {
            1: {
                'id': MAIN_BUTTON_ACTION_1,
                'modul': '',
                'action': '',
                },
            2: {
                'id': MAIN_BUTTON_ACTION_2,
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
        self.visible = True
        if self.isChild:
            self.setFocusId(self.guiMenList)
            self.onFocus(self.guiMenList)
            return
        self.setProperty('arch', oe.ARCHITECTURE)
        self.setProperty('distri', oe.DISTRIBUTION)
        self.setProperty('version', oe.VERSION)
        self.setProperty('build', oe.BUILD)
        oe.winOeMain = self
        for strModule in sorted(oe.dictModules, key=lambda x: list(oe.dictModules[x].menu.keys())):
            module = oe.dictModules[strModule]
            log.log(f'init module: {strModule}', log.DEBUG)
            if module.ENABLED:
                if hasattr(module, 'do_init'):
                    Thread(target=module.do_init).start() # Corrected threading call
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

    @log.log_function()
    def addMenuItem(self, strName, dictProperties):
        lstItem = xbmcgui.ListItem(label=oe._(strName))
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
        self.getControl(MAIN_CONTROL_SETTINGS_LIST).reset()
        m_menu = []
        for category in sorted(struct, key=lambda x: struct[x]['order']):
            if not 'hidden' in struct[category]:
                if fltr == []:
                    m_entry = {}
                    m_entry['name'] = oe._(struct[category]['name'])
                    m_entry['properties'] = {'typ': 'separator'}
                    m_entry['list'] = MAIN_CONTROL_SETTINGS_LIST
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
                            m_entry['list'] = MAIN_CONTROL_SETTINGS_LIST
                            m_menu.append(m_entry)
                        else:
                            if struct[category]['settings'][setting['parent']['entry']]['value'] in setting['parent']['value']:
                                if not 'optional' in setting or 'optional' in setting and optional != '0':
                                    m_entry['name'] = name
                                    m_entry['properties'] = dictProperties
                                    m_entry['list'] = MAIN_CONTROL_SETTINGS_LIST
                                    m_menu.append(m_entry)
        for m_entry in m_menu:
            self.addConfigItem(m_entry['name'], m_entry['properties'], m_entry['list']) # m_entry['list'] is already MAIN_CONTROL_SETTINGS_LIST

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
        actionId = -1 # Initialize actionId to a non-triggering value
        try:
            focusId = self.getFocusId()
            actionId = int(action.getId()) # Assign within try block
            if focusId == MAIN_SPECIFIC_FOCUS_ID_2222: # Was 2222
                if actionId == 61453: # Specific case to ignore (ACTION_MOUSE_WHEEL_UP or similar)
                    return
            if actionId in oe.CANCEL:
                self.visible = False
                self.close()
                return # Action handled, exit
            
            # ... other existing logic for non-CANCEL actions ...
            if focusId == self.guiList:
                curPos = self.getControl(focusId).getSelectedPosition()
                listSize = self.getControl(focusId).size()
                newPos = curPos
                nextItem = self.getControl(focusId).getListItem(newPos)
                if (curPos != self.lastGuiList or nextItem.getProperty('typ') == 'separator') and actionId in [
                    2, # ACTION_MOVE_DOWN
                    3, # ACTION_MOVE_UP
                    4, # ACTION_MOVE_RIGHT (often same as down in lists)
                    ]:
                    while nextItem.getProperty('typ') == 'separator':
                        if actionId == 2: # Down
                            newPos = newPos + 1
                        elif actionId == 3: # Up
                            newPos = newPos - 1
                        elif actionId == 4: # Right (treat as Down for this list logic)
                            newPos = newPos + 1
                        
                        # Boundary checks
                        if newPos < 0:
                            newPos = listSize - 1
                        elif newPos >= listSize:
                            newPos = 0
                        
                        nextItem = self.getControl(focusId).getListItem(newPos)
                    self.lastGuiList = newPos
                    self.getControl(focusId).selectItem(newPos)
                    self.setProperty('InfoText', nextItem.getProperty('InfoText'))
            
            if focusId == self.guiMenList:
                # This part of the original code seems to just set focus to itself,
                # which might be redundant or part of a larger logic flow.
                # Keeping it for now unless specified otherwise.
                self.setFocusId(focusId)

        except Exception as e:
            log.log(f"Error in onAction: {e!r}. Action was: {action!r}", log.ERROR)
            # Attempt to close if it was a cancel action, checking action directly
            try:
                if action and hasattr(action, 'getId') and action.getId() in oe.CANCEL:
                    self.visible = False # Ensure self.visible is set if it's used to control closing
                    self.close()
                else:
                    # If not a clear cancel action that caused the error,
                    # consider whether to close or just log.
                    # For now, let's stick to closing only on explicit CANCEL IDs
                    # that are identifiable. If action.getId() itself failed, this won't close.
                    pass # Or re-raise e if preferred, but UI code often tries to avoid full crashes.
            except Exception as final_e:
                log.log(f"Further error in onAction's except block: {final_e!r}", log.ERROR)
                # Fallback, perhaps try to close if self.visible indicates it should
                if hasattr(self, 'visible') and self.visible: # Check if closing is even relevant
                     try:
                         self.close()
                     except:
                         pass # Last resort

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
                if self.lastListType == int(selectedMenuItem.getProperty('listTyp')): # listTyp comes from oe.listObject
                    self.getControl(int(selectedMenuItem.getProperty('listTyp'))).setAnimations([('conditional', # listTyp comes from oe.listObject
                            'effect=fade start=100 end=0 time=100 condition=True')])
                self.getControl(MAIN_CONTROL_SETTINGS_LIST).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                self.getControl(MAIN_CONTROL_NETWORK_LIST).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                self.getControl(MAIN_CONTROL_BLUETOOTH_LIST).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                self.getControl(MAIN_CONTROL_OTHER_LIST).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                self.lastModul = selectedMenuItem.getProperty('Modul') # Corrected from 'modul' to 'Modul' if property name is case sensitive
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
        self.getControl(PINKEY_LABEL_TITLE).setLabel(text)

    def set_label1(self, text):
        self.getControl(PINKEY_LABEL_LINE1).setLabel(str(text))

    def set_label2(self, text):
        self.getControl(PINKEY_LABEL_LINE2).setLabel(str(text))

    def set_label3(self, text):
        self.getControl(PINKEY_LABEL_PIN_DISPLAY).setLabel(str(text))

    def append_label3(self, text):
        label = self.getControl(PINKEY_LABEL_PIN_DISPLAY).getLabel()
        self.getControl(PINKEY_LABEL_PIN_DISPLAY).setLabel(label + str(text))

    def get_label3_len(self):
        return len(self.getControl(PINKEY_LABEL_PIN_DISPLAY).getLabel())


class wizard(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.visible = False
        self.lastMenu = -1
        self.guiMenList = WIZARD_CONTROL_MENU_LIST # Assuming this is distinct from MAIN_CONTROL_MENU_LIST
        self.guiNetList = WIZARD_CONTROL_NETWORK_LIST
        self.wizTextbox = WIZARD_TEXTBOX
        self.wizTitle = WIZARD_LABEL_TITLE
        self.wizBtnTitle = WIZARD_LABEL_BUTTON_AREA_TITLE
        self.wizLstTitle = WIZARD_LABEL_LIST_AREA_TITLE
        self.wizWinTitle = 32300 # This is a string ID for localization, keep as is.
        self.guisettings = f'{oe.XBMC_USER_HOME}/userdata/guisettings.xml'
        self.buttons = {
            1: { # Next/Finish
                'id': WIZARD_BUTTON_NEXT_FINISH,
                'modul': '',
                'action': '',
                },
            2: { # Skip/Cancel
                'id': WIZARD_BUTTON_SKIP_CANCEL,
                'modul': '',
                'action': '',
                },
            3: { # Custom 1
                'id': WIZARD_BUTTON_CUSTOM_1,
                'modul': '',
                'action': '',
                },
            4: { # Custom 2
                'id': WIZARD_BUTTON_CUSTOM_2,
                'modul': '',
                'action': '',
                },
            }

        self.radiobuttons = {
            1: {
                'id': WIZARD_RADIOBUTTON_1,
                'modul': '',
                'action': '',
                },
            2: {
                'id': WIZARD_RADIOBUTTON_2,
                'modul': '',
                'action': '',
                },
            }

        self.actions = {}
        self.wizards = []
        self.last_wizard = None

    @log.log_function()
    def onInit(self):
        self.visible = True
        self.setProperty('arch', oe.ARCHITECTURE)
        self.setProperty('distri', oe.DISTRIBUTION)
        self.setProperty('version', oe.VERSION)
        self.setProperty('build', oe.BUILD)
        oe.dictModules['system'].do_init()
        self.getControl(self.wizWinTitle).setLabel(oe._(32300)) # wizWinTitle is a string ID, not a numeric control ID.
        self.getControl(WIZARD_BUTTON_CUSTOM_1).setVisible(False)
        self.getControl(WIZARD_BUTTON_CUSTOM_2).setVisible(False)
        self.getControl(WIZARD_RADIOBUTTON_1).setVisible(False)
        self.getControl(WIZARD_RADIOBUTTON_2).setVisible(False)
        self.getControl(WIZARD_BUTTON_SKIP_CANCEL).setVisible(False)
        if oe.BOOT_STATUS == "SAFE":
            self.set_wizard_title(f"[COLOR red][B]{oe._(32393)}[/B][/COLOR]")
            self.set_wizard_text(oe._(32394))
        else:
            self.set_wizard_title(oe._(32301))
            self.set_wizard_text(oe._(32302))
            oe.winOeMain.set_wizard_button_title(oe._(32310))
            cur_lang = xbmc.getLanguage()
            oe.winOeMain.set_wizard_button_1(cur_lang, self, 'wizard_set_language')
        self.showButton(1, 32303) # Button 1 is WIZARD_BUTTON_NEXT_FINISH
        self.setFocusId(WIZARD_BUTTON_NEXT_FINISH)

    @log.log_function()
    def wizard_set_language(self):
        global lang_new
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
            lang_new = langCodes[langKey]
            if lang_new == "resource.language.en_gb":
                oe.write_setting("system", "language", "")
            else:
                oe.write_setting("system", "language", str(lang_new))
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
        pass

    @log.log_function()
    def onClick(self, controlID):
        global strModule
        global prevModule
        log.log(f'{str(controlID)}: enter_function', log.DEBUG)
        for btn in self.buttons:
            # Check custom buttons (3 and 4)
            if controlID == WIZARD_BUTTON_CUSTOM_1 or controlID == WIZARD_BUTTON_CUSTOM_2:
                # Find which button (3 or 4) was clicked to get its specific module and action
                button_key_to_check = 3 if controlID == WIZARD_BUTTON_CUSTOM_1 else 4
                if hasattr(self.buttons[button_key_to_check]['modul'], self.buttons[button_key_to_check]['action']):
                    getattr(self.buttons[button_key_to_check]['modul'], self.buttons[button_key_to_check]['action'])()
        
        for btn_key in self.radiobuttons: # Iterate by key (1, 2)
            if controlID == self.radiobuttons[btn_key]['id']:
                if hasattr(self.radiobuttons[btn_key]['modul'], self.radiobuttons[btn_key]['action']):
                    getattr(self.radiobuttons[btn_key]['modul'], self.radiobuttons[btn_key]['action'])()

        if controlID == self.guiNetList: # WIZARD_CONTROL_NETWORK_LIST
            selectedItem = self.getControl(controlID).getSelectedItem() # controlID here is WIZARD_CONTROL_NETWORK_LIST
            if selectedItem.getProperty('action') != '':
                if hasattr(oe.dictModules[self.last_wizard], selectedItem.getProperty('action')):
                    getattr(oe.dictModules[self.last_wizard], selectedItem.getProperty('action'))(selectedItem)
                    return
        
        if controlID == WIZARD_BUTTON_SKIP_CANCEL:
            self.wizards.remove(strModule)
            oe.remove_node(strModule)
            if strModule == "system": # This is a string comparison, not an ID
                self.onInit()
            else:
                self.wizards.remove(prevModule)
                oe.remove_node(prevModule)
                self.onClick(WIZARD_BUTTON_NEXT_FINISH)
            log.log(f'{str(controlID)}: exit_function', log.DEBUG)

        if controlID == WIZARD_BUTTON_NEXT_FINISH:
            self.getControl(WIZARD_PROGRESS_INDICATOR_LABEL).setLabel('1')
            oe.xbmcm.waitForAbort(0.5)
            self.is_last_wizard = True
            self.getControl(WIZARD_AUX_LABEL).setLabel('')
            self.getControl(WIZARD_BUTTON_CUSTOM_1).setVisible(False)
            self.getControl(WIZARD_BUTTON_CUSTOM_2).setVisible(False)
            self.getControl(WIZARD_RADIOBUTTON_1).setVisible(False)
            self.getControl(WIZARD_RADIOBUTTON_2).setVisible(False)
            self.showButton(2, 32307) # Button 2 maps to WIZARD_BUTTON_SKIP_CANCEL
            self.set_wizard_title('')
            self.set_wizard_text('')
            self.set_wizard_list_title('')
            self.set_wizard_button_title('')

            if strModule == 'connman':
                xbmc.executebuiltin('UpdateAddonRepos')

            for module in sorted(oe.dictModules, key=lambda x: list(oe.dictModules[x].menu.keys())):
                strModule = module
                if hasattr(oe.dictModules[strModule], 'do_wizard') and oe.dictModules[strModule].ENABLED:
                    if strModule == self.last_wizard:
                        if hasattr(oe.dictModules[strModule], 'exit'):
                            oe.dictModules[strModule].exit()
                            if hasattr(oe.dictModules[strModule], 'is_wizard'):
                                del oe.dictModules[strModule].is_wizard
                    setting = oe.read_setting(strModule, 'wizard_completed')
                    if self.wizards != []:
                        prevModule = self.wizards[-1]
                    if oe.read_setting(strModule, 'wizard_completed') == None and strModule not in self.wizards:
                        self.last_wizard = strModule
                        if hasattr(oe.dictModules[strModule], 'do_init'):
                            oe.dictModules[strModule].do_init()
                        self.getControl(WIZARD_PROGRESS_INDICATOR_LABEL).setLabel('')
                        oe.dictModules[strModule].do_wizard()
                        self.wizards.append(strModule)
                        oe.write_setting(strModule, 'wizard_completed', 'True')
                        self.is_last_wizard = False
                        break
            if self.is_last_wizard == True:
                if lang_new and xbmc.getCondVisibility(f'System.HasAddon({lang_new})') == False:
                    xbmc.executebuiltin(f'InstallAddon({lang_new})')
                oe.xbmcm.waitForAbort(0.5)
                xbmc.executebuiltin('SendClick(10100,11)')
                oe.write_setting('libreelec', 'wizard_completed', 'True')
                self.visible = False
                self.close()
                if lang_new:
                    for _ in range(20):
                        if xbmc.getCondVisibility(f'System.HasAddon({lang_new})'):
                            break
                        oe.xbmcm.waitForAbort(0.5)
                    if xbmc.getCondVisibility(f'System.HasAddon({lang_new})') == True:
                        xbmc.executebuiltin(f'SetGUILanguage({str(lang_new)})')
                    else:
                        log.log(f'{str(controlID)}: ERROR: Unable to switch language to: {lang_new}. Language addon is not installed.', log.INFO)
        log.log(f'{str(controlID)}: exit_function', log.DEBUG)

    def onFocus(self, controlID):
        pass

    @log.log_function()
    def showButton(self, number, name):
        button = self.getControl(self.buttons[number]['id'])
        button.setLabel(oe._(name))
        button.setVisible(True)

    @log.log_function()
    def addConfigItem(self, strName, dictProperties, strType):
        lstItem = xbmcgui.ListItem(label=strName)
        for strProp in dictProperties:
            lstItem.setProperty(strProp, str(dictProperties[strProp]))
        self.getControl(int(strType)).addItem(lstItem)
        return lstItem
