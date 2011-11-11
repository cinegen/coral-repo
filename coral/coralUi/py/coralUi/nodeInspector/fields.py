# <license>
# Copyright (C) 2011 Andrea Interguglielmi, All rights reserved.
# This file is part of the coral repository downloaded from http://code.google.com/p/coral-repo.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# </license>


import weakref
from PyQt4 import QtGui, QtCore

import nodeInspector
from .. import mainWindow
from ... import coralApp
from ... import utils
from ...observer import Observer

class ObjectField(QtGui.QWidget):
    def __init__(self, label, coralObject, parentWidget):
        QtGui.QWidget.__init__(self, parentWidget)
        
        self._mainLayout = QtGui.QHBoxLayout(self)
        self._label = QtGui.QLabel(label, self)
        self._valueWidget = None
        self._coralObject = weakref.ref(coralObject)
        
        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)
        self._mainLayout.addWidget(self._label)
        
        self.connect(mainWindow.MainWindow.globalInstance(), QtCore.SIGNAL("coralExternalThreadActive(bool)"), self.setExternalThreadSpinning)
    
    def setExternalThreadSpinning(self, value, force = False):
        if self.valueWidget().isEnabled() == False or force == True:
            if value:
                self.valueWidget().setVisible(False)
                self.label().setText(self.label().text() + ": spinning")
            else:
                self.label().setText(str(self.label().text()).strip(": spinning"))
                self.valueWidget().setVisible(True)
    
    def label(self):
        return self._label
    
    def valueWidget(self):
        return self._valueWidget
    
    def setObjectWidget(self, widget, endOfEditSignal, endOfEditCallback):
        self._valueWidget = widget
        self._mainLayout.addWidget(widget)
        
        self.connect(self._valueWidget, QtCore.SIGNAL(endOfEditSignal), endOfEditCallback)
    
    def coralObject(self):
        return self._coralObject()

class AttributeField(ObjectField):
    def __init__(self, coralAttribute, parentWidget):
        ObjectField.__init__(self, coralAttribute.name().split(":")[-1], coralAttribute, parentWidget)
        
        self._valueChangedObserver = Observer()
        self._sourceAttributes = self._findSourceAttributes()
        
        coralApp.addAttributeValueChangedObserver(self._valueChangedObserver, self._sourceAttributes[0](), self.attributeValueChanged)
    
    def widgetValueChanged(self):
        value = self.getWidgetValue(self.valueWidget())
        for sourceAttr in self._sourceAttributes:
            attr = sourceAttr()
            if self.getAttributeValue(attr) != value:
                self.setAttributeValue(attr, value)
        
        self.coralObject().forceDirty()
    
    def attributeValueChanged(self):
        value = self.getAttributeValue(self._sourceAttributes[0]())
        if value != self.getWidgetValue(self.valueWidget()):
            self.setWidgetValue(self.valueWidget(), value)
    
    def getWidgetValue(self, widget):
        return None
    
    def setWidgetValue(self, widget):
        pass
    
    def getAttributeValue(self, attribute):
        return None
    
    def setAttributeValue(self, attribute, value):
        pass
    
    def setAttributeWidget(self, widget, endOfEditSignal):
        ObjectField.setObjectWidget(self, widget, endOfEditSignal, self.widgetValueChanged)
        
        attribute = self.coralObject()
        if attribute.input() or attribute.affectedBy():
            self.label().setText(">" + self.label().text())
            
        self.attributeValueChanged()
    
    def _collectOutAttrsNonPass(self, attribute, outAttrs):
        if attribute.isPassThrough() == False:
            outAttrs.append(weakref.ref(attribute))
        else:
            for outAttr in attribute.outputs():
                self._collectOutAttrsNonPass(outAttr, outAttrs)
	
    def _findSourceAttributes(self):
        attr = self.coralObject()
        attrs = []
        if attr.isPassThrough():
            self._collectOutAttrsNonPass(attr, attrs)
        if len(attrs) == 0:
            attrs = [weakref.ref(attr)]
        
        return attrs

class CustomDoubleSpinBox(QtGui.QDoubleSpinBox):
    def __init__(self, parent):
        QtGui.QDoubleSpinBox.__init__(self, parent)
        self.setDecimals(4)
        self._wheelCallback = None
    
    def wheelEvent(self, wheelEvent):
        QtGui.QDoubleSpinBox.wheelEvent(self, wheelEvent)
        
        self._wheelCallback()

class FloatValueField(AttributeField):
    def __init__(self, coralAttribute, parentWidget):
        AttributeField.__init__(self, coralAttribute, parentWidget)
        
        attrWidget = CustomDoubleSpinBox(self)
        attrWidget._wheelCallback = utils.weakRef(self.widgetValueChanged)
        attrWidget.setRange(-99999999999.0, 99999999999.0)
        attrWidget.setSingleStep(0.1)
        
        self.setAttributeWidget(attrWidget, "editingFinished()")
    
    def setAttributeValue(self, attribute, value):
        attribute.outValue().setFloatValueAt(0, value)
    
    def getAttributeValue(self, attribute):
        return attribute.value().floatValueAt(0)
    
    def setWidgetValue(self, widget, value):
        widget.setValue(value)
    
    def getWidgetValue(self, widget):
        return widget.value()

class CustomIntSpinBox(QtGui.QSpinBox):
    def __init__(self, parent):
        QtGui.QSpinBox.__init__(self, parent)
        
        self._wheelCallback = None
    
    def wheelEvent(self, wheelEvent):
        QtGui.QSpinBox.wheelEvent(self, wheelEvent)
        
        self._wheelCallback()
        
class IntValueField(AttributeField):
    def __init__(self, coralAttribute, parentWidget):
        AttributeField.__init__(self, coralAttribute, parentWidget)
        
        attrWidget = CustomIntSpinBox(self)
        attrWidget._wheelCallback = utils.weakRef(self.widgetValueChanged)
        attrWidget.setRange(-999999999, 999999999)
        
        self.setAttributeWidget(attrWidget, "editingFinished()")
        
    def setAttributeValue(self, attribute, value):
        attribute.outValue().setIntValueAt(0, value)
    
    def getAttributeValue(self, attribute):
        return attribute.value().intValueAt(0)
    
    def setWidgetValue(self, widget, value):
        widget.setValue(value)
    
    def getWidgetValue(self, widget):
        return widget.value()

class BoolValueField(AttributeField):
    def __init__(self, coralAttribute, parentWidget):
        AttributeField.__init__(self, coralAttribute, parentWidget)
        
        attrWidget = QtGui.QCheckBox(self)
        attrWidget.setTristate(False)
        self.setAttributeWidget(attrWidget, "stateChanged(int)")
        
    def setAttributeValue(self, attribute, value):
        attribute.outValue().setBoolValueAt(0, value)
    
    def getAttributeValue(self, attribute):
        return attribute.value().boolValueAt(0)
    
    def setWidgetValue(self, widget, value):
        widget.setCheckState(value)
    
    def getWidgetValue(self, widget):
        return widget.isChecked()

class StringValueField(AttributeField):
    def __init__(self, coralAttribute, parentWidget):
        AttributeField.__init__(self, coralAttribute, parentWidget)
        
        self.setAttributeWidget(QtGui.QLineEdit(self), "editingFinished()")
    
    def setAttributeValue(self, attribute, value):
        attribute.outValue().setStringValue(value)
    
    def getAttributeValue(self, attribute):
        return attribute.value().stringValue()
    
    def setWidgetValue(self, widget, value):
        widget.setText(value)
    
    def getWidgetValue(self, widget):
        return str(widget.text())

class NameField(ObjectField):
    def __init__(self, coralNode, parentWidget):
        ObjectField.__init__(self, "name", coralNode, parentWidget)
        
        self._nameChangedObserver = Observer()
        
        self.setObjectWidget(QtGui.QLineEdit(coralNode.name(), self), "editingFinished()", self.widgetValueChanged)
        
        coralApp.addNameChangedObserver(self._nameChangedObserver, coralNode, self._nameChanged)
    
    def widgetValueChanged(self):
        newName = str(self.valueWidget().text())
        if self.coralObject().name() != newName:
            self.coralObject().setName(newName)
    
    def _nameChanged(self):
        newName = self.coralObject().name()
        if newName != str(self.valueWidget().text()):
            self.valueWidget().setText(newName)
        