import os
import unittest
from __main__ import vtk, qt, ctk, slicer
import math

#
# CurveMaker
#

class CurveMaker:
  def __init__(self, parent):
    parent.title = "Curve Maker"
    parent.categories = ["Informatics"]
    parent.dependencies = []
    parent.contributors = ["Junichi Tokuda (BWH)"]
    parent.helpText = """
    This module generates a 3D curve model that connects fiducials listed in a given markup node. 
    """
    parent.acknowledgementText = """
    This work was supported by National Center for Image Guided Therapy (P41EB015898). The module is based on a template developed by Jean-Christophe Fillion-Robin, Kitware Inc. and Steve Pieper, Isomics, Inc. partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.
    self.parent = parent


#
# qCurveMakerWidget
#

class CurveMakerWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()
    self.logic = CurveMakerLogic()

  def setup(self):
    # Instantiate and connect widgets ...

    ####################
    # For debugging
    #
    ## Reload and Test area
    #reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    #reloadCollapsibleButton.text = "Reload && Test"
    #self.layout.addWidget(reloadCollapsibleButton)
    #reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)
    #
    ## reload button
    ## (use this during development, but remove it when delivering
    ##  your module to users)
    #self.reloadButton = qt.QPushButton("Reload")
    #self.reloadButton.toolTip = "Reload this module."
    #self.reloadButton.name = "CurveMaker Reload"
    #reloadFormLayout.addWidget(self.reloadButton)
    #self.reloadButton.connect('clicked()', self.onReload)
    #
    ####################

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # Source points (vtkMRMLMarkupsFiducialNode)
    #
    self.SourceSelector = slicer.qMRMLNodeComboBox()
    self.SourceSelector.nodeTypes = ( ("vtkMRMLMarkupsFiducialNode"), "" )
    self.SourceSelector.addEnabled = False
    self.SourceSelector.removeEnabled = False
    self.SourceSelector.noneEnabled = True
    self.SourceSelector.showHidden = False
    self.SourceSelector.renameEnabled = True
    self.SourceSelector.showChildNodeTypes = False
    self.SourceSelector.setMRMLScene( slicer.mrmlScene )
    self.SourceSelector.setToolTip( "Pick up a Markups node listing fiducials." )
    parametersFormLayout.addRow("Source points: ", self.SourceSelector)

    #
    # Target point (vtkMRMLMarkupsFiducialNode)
    #
    self.DestinationSelector = slicer.qMRMLNodeComboBox()
    self.DestinationSelector.nodeTypes = ( ("vtkMRMLModelNode"), "" )
    self.DestinationSelector.addEnabled = True
    self.DestinationSelector.removeEnabled = False
    self.DestinationSelector.noneEnabled = True
    self.DestinationSelector.showHidden = False
    self.DestinationSelector.renameEnabled = True
    self.DestinationSelector.selectNodeUponCreation = True
    self.DestinationSelector.showChildNodeTypes = False
    self.DestinationSelector.setMRMLScene( slicer.mrmlScene )
    self.DestinationSelector.setToolTip( "Pick up or create a Model node." )
    parametersFormLayout.addRow("Curve model: ", self.DestinationSelector)


    self.RadiusSliderWidget = ctk.ctkSliderWidget()
    self.RadiusSliderWidget.singleStep = 1.0
    self.RadiusSliderWidget.minimum = 1.0
    self.RadiusSliderWidget.maximum = 50.0
    self.RadiusSliderWidget.value = 5.0
    self.RadiusSliderWidget.setToolTip("Set the raidus of the tube.")
    parametersFormLayout.addRow("Radius: ", self.RadiusSliderWidget)

    #
    # check box to start curve visualization
    #
    self.EnableCheckBox = qt.QCheckBox()
    self.EnableCheckBox.checked = 0
    self.EnableCheckBox.setToolTip("If checked, the CurveMaker module keeps updating the model as the points are updated.")
    parametersFormLayout.addRow("Enable", self.EnableCheckBox)

    # connections
    self.EnableCheckBox.connect('toggled(bool)', self.onEnable)
    self.SourceSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.DestinationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.RadiusSliderWidget.connect("valueChanged(double)", self.onTubeUpdated)

    # Add vertical spacer
    self.layout.addStretch(1)
    
  def cleanup(self):
    pass

  def onEnable(self, state):
    if (state == True and self.SourceSelector.currentNode() != None and self.DestinationSelector.currentNode() != None):
      self.logic.activateEvent(self.SourceSelector.currentNode(), self.DestinationSelector.currentNode())
    else:
      self.logic.deactivateEvent()
      self.EnableCheckBox.setCheckState(False)

  def onSelect(self):
    if (self.SourceSelector.currentNode() == None or self.DestinationSelector.currentNode() == None):
      self.logic.deactivateEvent()
      self.EnableCheckBox.setCheckState(False)

  def onTubeUpdated(self):
    self.logic.setTubeRadius(self.RadiusSliderWidget.value)


  def onReload(self,moduleName="CurveMaker"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)


#
# CurveMakerLogic
#

class CurveMakerLogic:

  def __init__(self):
    self.SourceNode = None
    self.DestinationNode = None
    self.TubeRadius = 5.0
    self.NumberOfIntermediatePoints = 20

    self.tag = 0;

  def setNumberOfIntermediatePoints(self,npts):
    if npts > 0:
      self.NumberOfIntermediatePoints = npts

  def updatePoints(self):

      points = vtk.vtkPoints()
      cellArray = vtk.vtkCellArray()

      nPoints = self.SourceNode.GetNumberOfFiducials()
      points.SetNumberOfPoints(nPoints)
      x = [0.0, 0.0, 0.0]
      for i in range(nPoints):
        self.SourceNode.GetNthFiducialPosition(i, x)
        points.SetPoint(i, x);

      cellArray.InsertNextCell(nPoints)
      for i in range(nPoints):
        cellArray.InsertCellPoint(i)

      self.PolyData.SetPoints(points)
      self.PolyData.SetLines(cellArray)
      

  def updateCurve(self, caller, event):
    if (caller.IsA('vtkMRMLMarkupsFiducialNode') and event == 'ModifiedEvent'):

      self.updatePoints()
      
  def setTubeRadius(self, radius):

    self.TubeRadius = radius

    if (self.SourceNode and self.DestinationNode):
      self.TubeFilter.SetRadius(self.TubeRadius)
      self.updatePoints()
      lm = slicer.app.layoutManager()
      lm.activeThreeDRenderer().Render()

  def activateEvent(self, srcNode, destNode):
    if (srcNode and destNode):

      self.SourceNode = srcNode
      self.DestinationNode = destNode

      self.PolyData = vtk.vtkPolyData()
      self.updatePoints()

      self.SplineFilter = vtk.vtkSplineFilter()
      self.SplineFilter.SetInput(self.PolyData)
      self.SplineFilter.SetNumberOfSubdivisions(self.NumberOfIntermediatePoints*self.PolyData.GetPoints().GetNumberOfPoints())
      self.SplineFilter.Update()
      self.TubeFilter = vtk.vtkTubeFilter()
      self.TubeFilter.SetInputConnection(self.SplineFilter.GetOutputPort())
      self.TubeFilter.SetRadius(self.TubeRadius)
      self.TubeFilter.SetNumberOfSides(20)
      self.TubeFilter.CappingOn()

      # Add nodes to the scene
      if destNode.GetDisplayNodeID() == None:
        modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
        modelDisplayNode.SetColor(0.0,0.0,1.0)
        slicer.mrmlScene.AddNode(modelDisplayNode)
        destNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
      
      destNode.SetAndObservePolyData(self.TubeFilter.GetOutput())
      destNode.Modified()
      slicer.mrmlScene.AddNode(destNode)

      self.tag = self.SourceNode.AddObserver('ModifiedEvent', self.updateCurve)

  def addNewPoint(self,x,y,z):
    if (self.SourceNode and self.DestinationNode and self.PolyData):
      points = self.PolyData.GetPoints()
      cellArray = self.PolyData.GetLines()

      points.InsertNextPoint(x,y,z)
      cellArray.InsertCellPoint(self.PolyData.GetNumberOfPoints()-1)
      cellArray.UpdateCellCount(self.PolyData.GetNumberOfPoints())

      self.PolyData.SetPoints(points)
      self.PolyData.SetLines(cellArray)
      self.PolyData.Update()

      self.SourceNode.AddFiducial(x,y,z)

      self.activateEvent(self.SourceNode,self.DestinationNode)

  def getSplineFilterOutput(self):
    return self.SplineFilter.GetOutput()

  def getSplineFilterOutputPoints(self):
    if self.SplineFilter.GetOutput():
      return self.SplineFilter.GetOutput().GetPoints()

  def deactivateEvent(self):
    if (self.SourceNode):
      self.SourceNode.RemoveObserver(self.tag)
      self.SourceNode = None
      self.DestinationNode = None

