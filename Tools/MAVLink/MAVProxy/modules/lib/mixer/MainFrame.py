"""Subclass of MainFrameBase, which is generated by wxFormBuilder."""


import wx
import gui
import SubFunctionBlocks as FBlocksAPI
import subMAVFunctionSettings as MAVFSettingsAPI
import ValueEditor
import VirtualEditor
import pyCFiles as CFileGen
import SubpyFEditSettings as FESettings
import SubpyFEditProject as FEProject
import MAVlinkProcesses
import struct, array
import time 

import sys,os

from mixer_doc import callback_type
#import scanwin32


def PercentToQ14(percent):
    try:
        val = float(percent)
    except:
        val = 0.0;
    return (int) (val * 163.84)

class fifo(object):
    def __init__(self):
        self.buf = []
    
    def write(self, data):
        self.buf += data
        return len(data)
    
    def read(self):
        return self.buf.pop(0)
    
# find the mavlink.py module
for d in [ 'pymavlink',
          os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'MAVLink', 'pymavlink') ]:
    if os.path.exists(d):
        sys.path.insert(0, d)

    
#        if os.name == 'nt':
#            try:
#                # broken python compilation of mavlink.py on windows!
#                os.unlink(os.path.join(d, 'mavlink.pyc'))
#            except:
#                pass
#import mavutil

# Implementing MainFrameBase
class MainFrame( gui.MainFrameBase ):
    def __init__( self, parent, doc):
        gui.MainFrameBase.__init__( self, parent )
        
        self.doc = doc

        self.registers = self.doc.MAVFSettings.registers.register
        self.functions = self.doc.MAVFSettings.functions.function
        self.settings = self.doc.MAVFSettings
        self.FBlocks = self.doc.FBlocks        

        self.m_updateFunctionBlocks()

        self.exportPath = ''

        self.selectedFunctionIndex = 0
        self.selectedRegisterIndex = 0
        self.m_paramsEditIndex = -1
        
        self.m_refreshSettingsGrid()
        
        self.doc.m_register_callback(self.m_doc_update_callback)
    # Document handling
    
    def m_doc_update_callback(self, update_type, hint):
#        if(update_type == callback_type.UPDATED_ALL):
#            self.m_refreshSettingsGrid()
        if(update_type == callback_type.ONLINE):
            self.m_btUpdate.Enable(True)
        if(update_type == callback_type.OFFLINE):
            self.m_btUpdate.Enable(False)
        if(update_type == callback_type.SYNC_IN_PROGRESS):
            self.m_gridFBs.Enable(False)
            self.m_scrolledWindowFuncParams.Enable(False)
        if(update_type == callback_type.SYNC_COMPLETE):
            self.m_gridFBs.Enable(True)
            self.m_scrolledWindowFuncParams.Enable(True)
        if(update_type == callback_type.SYNC_FAIL):
            self.m_gridFBs.Enable(True)
            self.m_scrolledWindowFuncParams.Enable(True)            
           
            

    def m_updateFunctionBlocks(self):
        self.m_listBoxFuncType.Clear()
        FBlockNames = []
        for item in self.FBlocks:
            FBlockNames.append(item.header.name)
        self.m_listBoxFuncType.InsertItems(FBlockNames, 0)
              

    def m_findRegisterIndexWithName ( self, regName ):
        index = 0
        for item in self.registers:
            if regName == item.identifier:
                return index
            index = index + 1
        return -1

    def m_findTypeIndexWithName ( self, typeName ):
        print('Searching for function type ', typeName)
        index = 0
        for FBlock in self.FBlocks:
            if FBlock.header.name == typeName:
                return index
            index = index + 1
        return -1

        
    def m_refreshSettingsGrid( self ):

        self.refreshingSettingsGrid = True

        self.m_gridFBs.DeleteCols(0, self.m_gridFBs.GetNumberCols())
        self.m_gridFBs.DeleteRows(0, self.m_gridFBs.GetNumberRows())

        index = 0
        for item in self.registers:
            self.m_gridFBs.AppendCols(1)
            self.m_gridFBs.SetColLabelValue(index, item.identifier)
            index = index + 1

        index = 0
        for item in self.functions:
            self.m_gridFBs.AppendRows(1)
            self.m_refreshSettingsGridFunction( index )
            index = index + 1

        if(self.m_checkBoxAutoUpdate.GetValue() == True):
            self.m_mavlinkUpdate()

        self.m_gridFBs.AutoSizeColumns()

        self.refreshingSettingsGrid = False


    def m_refreshSettingsGridFunction( self, funcIndex):
        function = self.functions[funcIndex]
        destRegStr = function.header.destReg
        funcTypeStr = function.header.functionType
        funcAction = function.header.action
        regColumn = self.m_findRegisterIndexWithName(destRegStr)
        if regColumn == -1:
            print("ERROR: Could not find register with name " + destRegStr)
            return
        self.m_gridFBs.SetCellValue(funcIndex, regColumn, funcTypeStr)

        funcTypeIndex = self.m_findTypeIndexWithName( funcTypeStr )

        actionIndex = -1

        if funcAction == 'SET':
            self.m_gridFBs.SetCellTextColour(funcIndex,regColumn, wx.TheColourDatabase.Find("red") )
            actionIndex = 0
        elif funcAction == 'ADD':
            self.m_gridFBs.SetCellTextColour(funcIndex,regColumn, wx.TheColourDatabase.Find("black") )
            actionIndex = 1
        elif funcAction == 'CLEAR':
            self.m_gridFBs.SetCellTextColour(funcIndex,regColumn, wx.TheColourDatabase.Find("grey") )
            actionIndex = 2

        paramIndex = 0
        for parameter in function.setting:
            paramType = self.FBlocks[funcTypeIndex].setting[paramIndex].type_
            paramValue = self.functions[funcIndex].setting[paramIndex].value
            if paramType == 'Register':
                refIndex = self.m_findRegisterIndexWithName(parameter.value)
                if refIndex <> -1:
                    self.m_gridFBs.SetCellBackgroundColour(funcIndex, refIndex, wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT) )
            paramIndex = paramIndex + 1



    def m_refreshParametersGrid ( self ):
        if self.refreshingSettingsGrid == True:
            return

        print("refreshing parameter grid")
        for col in range(self.m_gridParameters.GetNumberCols()):
            for row in range(self.m_gridParameters.GetNumberRows()):
                self.m_gridParameters.SetCellValue(row, col, "")

        if self.selectedFunctionIndex <> -1:
            searchFuncType = self.functions[self.selectedFunctionIndex].header.functionType
            foundTypeIndex = self.m_findTypeIndexWithName( searchFuncType )             

            index = 0
            if(len(self.functions[self.selectedFunctionIndex].setting) > 0):
                for item in self.functions[self.selectedFunctionIndex].setting:
                    print("adding to parameter grid, foundType={:d}".format(foundTypeIndex))
                    typeData = self.FBlocks[foundTypeIndex].setting[index].type_
                    description = self.FBlocks[foundTypeIndex].setting[index].description                              
                    self.m_gridParameters.SetCellValue(index, 0, item.name)
                    self.m_gridParameters.SetCellValue(index, 1, item.value)
                    self.m_gridParameters.SetCellValue(index, 2, typeData)
                    self.m_gridParameters.SetCellValue(index, 3, description)
                    index = index + 1

            self.m_comboAction.SetValue(self.functions[self.selectedFunctionIndex].header.action)
            
    def m_selFunctionAtIndex ( self, index ):
        self.selectedFunctionIndex = index
        self.m_refreshParametersGrid()

    def m_clearSelectedFunctionParamList ( self ):
        del self.functions[self.selectedFunctionIndex].setting[:]
        print("clear parameters from function")

    def m_changeSelectedFunctionType ( self, functionTypeIndex ):
        self.m_clearSelectedFunctionParamList()
        prntstr = 'Change selected function type, function{:d}, type index{:d}'.format(self.selectedFunctionIndex, functionTypeIndex)
        print(prntstr)
        sourceFBlock = self.FBlocks[functionTypeIndex]
        self.functions[self.selectedFunctionIndex].header.functionType = sourceFBlock.header.name
        print("Setting function to name ", self.functions[self.selectedFunctionIndex].header.functionType)
        for item in self.FBlocks[functionTypeIndex].setting:
            newParameter = MAVFSettingsAPI.functionBlockDataSub(item.name, item.default)
            self.functions[self.selectedFunctionIndex].setting.append(newParameter)
            print("insert new parameter into function")
        self.m_refreshParametersGrid()
        self.m_refreshSettingsGrid()

    def m_menuGetUniqueRegisterName ( self ):
        found = False
        index = 1
        
        while found == False:
            searchStr = 'NULL_{:d}'.format(index)
            match = False
            for register in self.registers:
                if register.identifier == searchStr:
                    match = True
            if match == False:
                found = True
            index = index + 1
        return searchStr
            
                
    
    # Handlers for MainFrameBase events.

    def m_listBoxFuncTypeDClick ( self, event ):
        selections = self.m_listBoxFuncType.GetSelections()
        if len(selections) > 0:
            print("function type change")
            self.m_changeSelectedFunctionType( selections[0] )
        self.m_gridFBs.MakeCellVisible( self.selectedFunctionIndex, self.selectedRegisterIndex )
        event.Skip()

    def m_menuAddRegister ( self, event ):
        regstring = self.m_menuGetUniqueRegisterName()          #'NULL_{:d}'.format(len(self.registers) + 1)
        newreg = MAVFSettingsAPI.registerSub(regstring, "Does nothing")
        self.registers.append(newreg)
        self.m_refreshSettingsGrid()
        self.m_gridFBs.MakeCellVisible( self.selectedFunctionIndex, self.selectedRegisterIndex )
        event.Skip()

    def m_menuInsertRegister ( self, event ):
        regstring =  self.m_menuGetUniqueRegisterName()         #'NULL_{:d}'.format(len(self.registers) + 1)
        newreg = MAVFSettingsAPI.registerSub(regstring, "Does nothing")
        self.registers.insert( self.selectedRegisterIndex, newreg)
        self.m_refreshSettingsGrid()
        self.m_gridFBs.MakeCellVisible( self.selectedFunctionIndex, self.selectedRegisterIndex )
        event.Skip()

    def m_menuDeleteRegister ( self, event ):
        self.registers.pop(self.selectedRegisterIndex)
        self.selectedRegisterIndex = 0
        self.m_refreshSettingsGrid()        
        self.m_gridFBs.MakeCellVisible( self.selectedFunctionIndex, self.selectedRegisterIndex )
        event.Skip()

    def m_menuAddFunction ( self, event ):
        newFHeader = MAVFSettingsAPI.functionBlockHeaderSub("NULL", "NULL", "CLEAR", "Do nothing")
        newFSettings = []
        newfunc = MAVFSettingsAPI.functionSub(newFHeader, newFSettings)
        self.MAVFSettings.functions.function.append(newfunc)
        self.m_refreshSettingsGrid()
        self.m_gridFBs.MakeCellVisible( self.selectedFunctionIndex, self.selectedRegisterIndex )
        event.Skip()        

    def m_menuInsertFunction ( self, event ):
        newFHeader = MAVFSettingsAPI.functionBlockHeaderSub("NULL", "NULL", "CLEAR", "Do nothing")
        newFSettings = []
        newfunc = MAVFSettingsAPI.functionSub(newFHeader, newFSettings)
        self.MAVFSettings.functions.function.insert(self.selectedFunctionIndex, newfunc)
        self.m_refreshSettingsGrid()
        self.m_gridFBs.MakeCellVisible( self.selectedFunctionIndex, self.selectedRegisterIndex )
        event.Skip()

    def m_menuDeleteFunction ( self, event ):
        self.MAVFSettings.functions.function.pop(self.selectedFunctionIndex)
        self.selectedFunctionIndex = 0
        self.m_refreshSettingsGrid()        
        self.m_gridFBs.MakeCellVisible( self.selectedFunctionIndex, self.selectedRegisterIndex )
        event.Skip()

            
    def m_FBs_cell_click ( self, event ):
        if self.refreshingSettingsGrid == False:
            print("Click cell on row", event.GetRow() )
            self.selectedRegisterIndex = event.GetCol()
            self.m_selFunctionAtIndex(event.GetRow())
        event.Skip()

    def m_FBs_cell_dclick ( self, event ):
        self.selectedFunctionIndex = event.GetRow()
        self.selectedRegisterIndex = event.GetCol()
        identifier = self.MAVFSettings.registers.register[event.GetCol()].identifier
        print("double cell click")
        self.MAVFSettings.functions.function[event.GetRow()].header.destReg = identifier
        self.m_refreshSettingsGrid()
        self.m_gridFBs.MakeCellVisible( event.GetRow(), event.GetCol() )
        event.Skip()

    def m_FBs_label_click ( self, event ):
        self.selectedRegisterIndex = event.GetCol()
        print("label click")

        if self.m_paramsEditIndex == -1:
            event.Skip()
            print("no parameter being edited")
            return
        
        if self.m_gridParameters.IsCellEditControlEnabled():
            if self.m_gridParameters.GetCellValue(self.m_paramsEditIndex, 2) != 'Register':
                print("not a Register type, value not set")
                event.Skip()
                return
            print("params edit set to label value")
            editCntrl = self.m_gridParameters.GetCellEditor(self.m_paramsEditIndex, 1)
            regName = self.MAVFSettings.registers.register[event.GetCol()].identifier

            self.m_gridParameters.SetCellValue(self.m_paramsEditIndex, 1, regName)
            self.MAVFSettings.functions.function[self.selectedFunctionIndex].setting[self.m_paramsEditIndex].value = regName
            print('Changing function ', self.selectedFunctionIndex, ' parameter ', self.m_paramsEditIndex, ' to ', regName)
            self.m_refreshSettingsGridFunction( self.selectedFunctionIndex )
            self.m_paramsEditIndex == -1
        event.Skip()

    def   m_FBs_right_click ( self, event ):
        self.PopupMenu( self.m_menuGrid ) 
        event.Skip()

    def   m_FBs_regEdit ( self, event ):
        regNameEditor = ValueEditor.ValueEditDialog( self )
        regNameEditor.m_textCtrlRegNameEdit.SetValue(self.m_gridFBs.GetColLabelValue( event.GetCol() ))
        regNameEditor.ShowModal()
        newRegName = str(regNameEditor.m_textCtrlRegNameEdit.GetValue())
        if newRegName.find(" ") != wx.NOT_FOUND:
            print("No spaces allowed in register names")
            event.Skip()
            return
        if len(newRegName) > 15:
            print("Name too long, reduce to less than 15 characters, no spaces")
            event.Skip()
            return
        if len(newRegName) == 0:
            print("Must be at least one character long")
            event.Skip()
            return
        self.MAVFSettings.registers.register[ event.GetCol() ].identifier = newRegName
        self.m_refreshSettingsGrid()
        self.m_gridFBs.MakeCellVisible( event.GetRow(), event.GetCol() )
        event.Skip()

    def   m_panelFBsize ( self, event ):
        frameSize = self.m_panelFBs.GetSize()
        gridSize = self.m_gridFBs.GetMaxSize()

        gridSize.SetWidth(frameSize.GetWidth() - 5)
        gridSize.SetHeight(frameSize.GetHeight() - 5)
        self.m_gridFBs.SetMaxSize(gridSize)
        self.m_gridFBs.SetMinSize(gridSize)
        event.Skip()

    def   m_comboSetAction ( self, event ):
        selString = self.m_comboAction.GetValue()
        self.MAVFSettings.functions.function[self.selectedFunctionIndex].header.action = selString
        self.m_refreshSettingsGridFunction( self.selectedFunctionIndex )
        event.Skip()

    def   m_ParamsCellSelect ( self, event ):
        self.m_paramsSelectIndex = event.GetRow()
        paramTypeName = self.m_gridParameters.GetCellValue(event.GetRow(), 2)
        paramValue = self.m_gridParameters.GetCellValue(event.GetRow(), 1)
        if paramTypeName == 'Percent':
            self.m_sliderParamValue.SetRange(-150, 150)
            self.m_sliderParamValue.SetTick(25)
            paramValInt = int(float(paramValue))
            self.m_sliderParamValue.SetValue(paramValInt)
            self.m_sliderParamValue.Enable()
        else:                
            self.m_sliderParamValue.Disable()
        event.Skip()                


    def   m_ParamsEditShow ( self, event ):
        print("params edit show")
        if event.GetCol() <> 1:
            self.m_paramsEditIndex = -1
        else:
            self.m_paramsEditIndex = event.GetRow()
            self.preEditParamValue = self.m_gridParameters.GetCellValue(event.GetRow(), event.GetCol() )
        event.Skip()                

    def   m_ParamsEditHide ( self, event ):
        print("params edit hide")
        CellEditor = self.m_gridParameters.GetCellEditor(event.GetRow(), event.GetCol())
#       self.m_paramsEditIndex = -1
        if event.GetCol() <> 1:
            CellEditor.Reset()
            print("params edit reset value")
            event.Skip()
            return
        event.Skip()

    def   m_ParamsCellChange ( self, event ):
        if event.GetCol() <> 1:
            self.m_gridParameters.SetCellValue(event.GetRow(), event.GetCol(), self.preEditParamValue)
            event.Skip()
            return           
            
        paramTypeName = self.m_gridParameters.GetCellValue(event.GetRow(), 2)
        paramEditStr = self.m_gridParameters.GetCellValue(event.GetRow(),1)
        
        if( self.doc.m_paramChange(self.selectedFunctionIndex, event.GetRow(), paramEditStr, paramTypeName) == False ):
            self.m_gridParameters.SetCellValue(event.GetRow(), event.GetCol(), self.preEditParamValue)
        else:
            self.m_refreshSettingsGridFunction( self.selectedFunctionIndex )   
            
        event.Skip()


    def m_scrollParamValue ( self, event ):
        if self.m_paramsSelectIndex == -1:
            event.Skip()
            return
        if self.m_sliderParamValue.IsEnabled() == False:
            event.Skip()
            return

        paramTypeName = self.m_gridParameters.GetCellValue(self.m_paramsSelectIndex, 2)
        if paramTypeName == 'Percent':
            newStrValue = "{:d}".format(self.m_sliderParamValue.GetValue())
            self.m_gridParameters.SetCellValue(self.m_paramsSelectIndex, 1,  newStrValue)
            self.MAVFSettings.functions.function[self.selectedFunctionIndex].setting[self.m_paramsSelectIndex].value = newStrValue
        event.Skip()

    def m_scrollParamRelease(self, event ):
        self.m_mavlinkUpdateFunction(self.selectedFunctionIndex)
        event.Skip()


    def m_mavlinkUpdateFunction ( self, functionIndex ):

        if(self.m_checkBoxAutoUpdate.GetValue() == False):
            self.doc.not_synchronised()
            return
        
        print("Starting single function update")
        self.m_gridFBs.Enable(False)
        self.m_scrolledWindowFuncParams.Enable(False)
        self.doc.m_updateFunction(self.selectedFunctionIndex)


    def m_mavlinkUpdate ( self ):
        print("Starting update")
        self.m_gridFBs.Enable(False)
        self.m_scrolledWindowFuncParams.Enable(False)
        self.doc.m_update()


    def m_btClick_Update ( self, event):
        self.m_mavlinkUpdate()
        event.Skip()

        
    def m_mniOpenSettingsClick( self, event ):
        fdlg = wx.FileDialog(self,"Open a settings file",wx.EmptyString,wx.EmptyString,"*.feset",wx.FD_OPEN | wx.FD_FILE_MUST_EXIST);
        if fdlg.ShowModal() != wx.ID_OK:
            return;
        self.m_openSettingsFile(fdlg.GetPath())
            
    def m_mniSaveSettingsClick( self, event ):
        self.m_saveSettingsFile("")

    def m_mniSaveSettingsAsClick( self, event ):
        fdlg = wx.FileDialog(self, "Save the settings file as", wx.EmptyString, wx.EmptyString, "*.feset", wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT);
        if fdlg.ShowModal() != wx.ID_OK:
            return;
        self.m_saveSettingsFile(fdlg.GetPath())

        
    def m_mniOpenProjectClick( self, event ):
        fdlg = wx.FileDialog(self,"Open a settings file",wx.EmptyString,wx.EmptyString,"*.fep",wx.FD_OPEN | wx.FD_FILE_MUST_EXIST);
        if fdlg.ShowModal() != wx.ID_OK:
            return;
        self.Settings.ProjectPath = fdlg.GetPath()
        self.m_openProject()
            
    def m_mniSaveProjectClick( self, event ):
        self.Project.SystemID = int(self.m_textCtrlSysID.GetValue())
        self.Project.ComponentID = int(self.m_textCtrlCompID.GetValue())

        FILE = open(self.Settings.ProjectPath, "w")
        if(not FILE.closed):            
            try:
                self.Project.export( FILE , 0 )
            except:
                print("could not export project file")
        

    def m_mniSaveProjectAsClick( self, event ):
        fdlg = wx.FileDialog(self, "Save the project file as", wx.EmptyString, wx.EmptyString, "*.fep", wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT);
        if fdlg.ShowModal() != wx.ID_OK:
            return;
        
        self.Project.SystemID = int(self.m_textCtrlSysID.GetValue())
        self.Project.ComponentID = int(self.m_textCtrlCompID.GetValue())

        FILE = open(fdlg.GetPath(), "w")
        try:
            self.Project.export( FILE , 0 )
        except:
            print("could not export project")
        else:
            self.Settings.ProjectPath = fdlg.GetPath()
            
    def m_btnClick_GenCCode(self, event):
        self.m_mnExportCHeaders(event)
        event.Skip()
        
    def m_mnExportCHeaders( self, event ):
        fdlg = wx.DirDialog(self);
        fdlg.SetPath(self.exportPath)
        if fdlg.ShowModal() != wx.ID_OK:
            return;

        self.exportPath = fdlg.GetPath()
        self.doc.m_mnExportCHeaders(self.exportPath)

    def m_btnClick_EditVirtual(self, event):
        self.m_mnEditVirtualisation(event)
        event.Skip()
            
    def m_mnEditVirtualisation(self, event ):
        VirtualEdit = VirtualEditor.VirtualEditDialog( self, self.doc )
        VirtualEdit.ShowModal()
        
    def m_btnClick_SaveNVMem(self, event):
        self.m_mnCommitToNV( event )
        event.Skip()
        
    def m_chkBox_autoUpdate(self, event):
        self.doc.m_set_autoUpdate(self.m_checkBoxAutoUpdate.GetValue())
        event.Skip()
                
    def m_mnCommitToNV(self, event ):
        try:
            self.MAVProcesses
        except:
            dlg = wx.MessageDialog(self, "MAVlink processes not running, connect to MAV first", "WARNING", wx.OK)
            dlg.ShowModal()
            return

        if(self.MAVProcesses.services_running() == False):
            dlg = wx.MessageDialog(self, "MAVlink processes not running, connect to MAV first", "WARNING", wx.OK)
            dlg.ShowModal()       
            return        
        
        dlg = wx.MessageDialog(self, "CONFIRM WRITE TO NON VOLATILE MEMORY", "NV memory write")
        if(dlg.ShowModal() != wx.ID_OK):
            return
        
        self.MAVProcesses.commit_buffer_to_nvmem();

    def m_btnClick_ClearNVMem(self, event):
        event.Skip()
            
    def m_mniExitClick( self, event ):
#        if self.MAVProcesses.services_running():
#            self.MAVProcesses.stop_services()

        self.doc.m_close()
                
        event.Skip()
    
    def m_mniAboutClick( self, event ):
        wx.MessageBox("oneminutepython template. ","oneminutepython")
    

