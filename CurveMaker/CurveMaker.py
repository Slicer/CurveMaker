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
    parent.contributors = ["Junichi Tokuda (BWH), Laurent Chauvin (BWH)"]
    parent.helpText = """
    This module generates a 3D curve model that connects fiducials listed in a given markup node. 
    """
    parent.acknowledgementText = """
    This work was supported by National Center for Image Guided Therapy (P41EB015898). The module is based on a template developed by Jean-Christophe Fillion-Robin, Kitware Inc. and Steve Pieper, Isomics, Inc. partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.
    self.parent = parent


#
# CurveMakerWidget
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
    self.tag = 0

  def setup(self):
    # Instantiate and connect widgets ...

    ####################
    # For debugging
    #
    # Reload and Test area
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "CurveMaker Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)
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
    self.SourceSelector.addEnabled = True
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
    self.SourceSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSourceSelected)
    self.DestinationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onDestinationSelected)
    self.RadiusSliderWidget.connect("valueChanged(double)", self.onTubeUpdated)

    # Add vertical spacer
    self.layout.addStretch(1)
    
  def cleanup(self):
    pass

  def onEnable(self, state):
    self.logic.enableAutomaticUpdate(state)

  def onSourceSelected(self):
    # Remove observer if previous node exists
    if self.logic.SourceNode and self.tag:
      self.logic.SourceNode.RemoveObserver(self.tag)

    # Update selected node, add observer, and update control points
    if self.SourceSelector.currentNode():
      self.logic.SourceNode = self.SourceSelector.currentNode()

      # Check if model has already been generated with for this fiducial list
      tubeModelID = self.logic.SourceNode.GetAttribute('CurveMaker.CurveModel')
      self.DestinationSelector.setCurrentNodeID(tubeModelID)

      self.tag = self.logic.SourceNode.AddObserver('ModifiedEvent', self.logic.controlPointsUpdated)

    # Update checkbox
    if (self.SourceSelector.currentNode() == None or self.DestinationSelector.currentNode() == None):
      self.EnableCheckBox.setCheckState(False)
    else:
      self.logic.SourceNode.SetAttribute('CurveMaker.CurveModel',self.logic.DestinationNode.GetID())
      self.logic.generateControlPolyData()

  def onDestinationSelected(self):
    # Update destination node
    if self.DestinationSelector.currentNode():
      self.logic.DestinationNode = self.DestinationSelector.currentNode()

    # Update checkbox
    if (self.SourceSelector.currentNode() == None or self.DestinationSelector.currentNode() == None):
      self.EnableCheckBox.setCheckState(False)
    else:
      self.logic.SourceNode.SetAttribute('CurveMaker.CurveModel',self.logic.DestinationNode.GetID())
      self.logic.generateControlPolyData()

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

    self.AutomaticUpdate = False
    self.NumberOfIntermediatePoints = 20
    self.ModelColor = [0.0, 0.0, 1.0]

    self.ControlPoints = None

  def setNumberOfIntermediatePoints(self,npts):
    if npts > 0:
      self.NumberOfIntermediatePoints = npts
    self.updateCurve()

  def setTubeRadius(self, radius):
    self.TubeRadius = radius
    self.updateCurve()

  def enableAutomaticUpdate(self, auto):
    self.AutomaticUpdate = auto
    self.generateControlPolyData()

  def controlPointsUpdated(self,caller,event):
    if caller.IsA('vtkMRMLMarkupsFiducialNode') and event == 'ModifiedEvent':
      self.generateControlPolyData()

  def generateControlPolyData(self):
    if self.SourceNode:
      points = vtk.vtkPoints()
      cellArray = vtk.vtkCellArray()

      nOfControlPoints = self.SourceNode.GetNumberOfFiducials()
      points.SetNumberOfPoints(nOfControlPoints)
      pos = [0.0, 0.0, 0.0]
      for i in range(nOfControlPoints):
        self.SourceNode.GetNthFiducialPosition(i,pos)
        points.SetPoint(i,pos)

      cellArray.InsertNextCell(nOfControlPoints)
      for i in range(nOfControlPoints):
        cellArray.InsertCellPoint(i)

      if self.ControlPoints == None:
        self.ControlPoints = vtk.vtkPolyData()
      self.ControlPoints.Initialize()

      self.ControlPoints.SetPoints(points)
      self.ControlPoints.SetLines(cellArray)

      if self.AutomaticUpdate:
        self.updateCurve()

  def updateCurve(self):
    if self.ControlPoints and self.DestinationNode:
      totalNumberOfPoints = self.NumberOfIntermediatePoints*self.ControlPoints.GetPoints().GetNumberOfPoints()

      splineFilter = vtk.vtkSplineFilter()
      if vtk.VTK_MAJOR_VERSION <= 5:
        splineFilter.SetInput(self.ControlPoints)
      else:
        splineFilter.SetInputData(self.ControlPoints)
      splineFilter.SetNumberOfSubdivisions(totalNumberOfPoints)
      splineFilter.Update()

      tubeFilter = vtk.vtkTubeFilter()
      tubeFilter.SetInputConnection(splineFilter.GetOutputPort())
      tubeFilter.SetRadius(self.TubeRadius)
      tubeFilter.SetNumberOfSides(20)
      tubeFilter.CappingOn()
      tubeFilter.Update()

      if self.DestinationNode.GetDisplayNodeID() == None:
        modelDisplayNode = slicer.vtkMRMLModelDisplayNode()
        modelDisplayNode.SetColor(self.ModelColor)
        slicer.mrmlScene.AddNode(modelDisplayNode)
        self.DestinationNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

      self.DestinationNode.SetAndObservePolyData(tubeFilter.GetOutput())
      self.DestinationNode.Modified()

      if self.DestinationNode.GetScene() == None:
        slicer.mrmlScene.AddNode(self.DestinationNode)

      return splineFilter.GetOutput()
