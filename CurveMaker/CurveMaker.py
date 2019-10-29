import os
import unittest
from __main__ import vtk, qt, ctk, slicer
import math
import numpy
from Endoscopy import EndoscopyComputePath

#
# CurveMaker
#

class CurveMaker:
  def __init__(self, parent):
    parent.title = "Curve Maker"
    parent.categories = ["Utilities"]
    parent.dependencies = []
    parent.contributors = ["Junichi Tokuda (BWH), Laurent Chauvin (BWH)"]
    parent.helpText = """
    This module generates a 3D curve model that connects fiducials listed in a given markup node. 
    """
    parent.acknowledgementText = """
    This work was supported by National Institutes of Health (P41EB015898, R01EB020667, R01CA235134).
    The module is based on a template developed by Jean-Christophe Fillion-Robin, Kitware Inc. and Steve Pieper, Isomics, Inc.
    partially funded by NIH grant 3P41RR013218-12S1.
    """
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
    #self.tag = 0

  def setup(self):
    # Instantiate and connect widgets ...
    self.RingOff = None
    self.RingOn = None

    # Tags to manage event observers
    # self.tagSourceNode = None
    self.tagDestinationNode = None
    
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

    #
    # Radius for the tube
    #
    self.RadiusSliderWidget = ctk.ctkSliderWidget()
    self.RadiusSliderWidget.singleStep = 1.0
    self.RadiusSliderWidget.minimum = 1.0
    self.RadiusSliderWidget.maximum = 50.0
    self.RadiusSliderWidget.value = 5.0
    self.RadiusSliderWidget.setToolTip("Set the raidus of the tube.")
    parametersFormLayout.addRow("Radius (mm): ", self.RadiusSliderWidget)

    #
    # Radio button to select interpolation method
    #
    self.InterpolationLayout = qt.QHBoxLayout()
    self.InterpolationNone = qt.QRadioButton("None")
    self.InterpolationCardinalSpline = qt.QRadioButton("Cardinal Spline")
    self.InterpolationHermiteSpline = qt.QRadioButton("Hermite Spline (for Endoscopy)")
    self.InterpolationLayout.addWidget(self.InterpolationNone)
    self.InterpolationLayout.addWidget(self.InterpolationCardinalSpline)
    self.InterpolationLayout.addWidget(self.InterpolationHermiteSpline)
    
    self.InterpolationGroup = qt.QButtonGroup()
    self.InterpolationGroup.addButton(self.InterpolationNone)
    self.InterpolationGroup.addButton(self.InterpolationCardinalSpline)
    self.InterpolationGroup.addButton(self.InterpolationHermiteSpline)

    parametersFormLayout.addRow("Interpolation: ", self.InterpolationLayout)

    #
    # Interpolation Resolution
    #
    self.InterpResolutionSliderWidget = ctk.ctkSliderWidget()
    self.InterpResolutionSliderWidget.singleStep = 1.0
    self.InterpResolutionSliderWidget.minimum = 5.0
    self.InterpResolutionSliderWidget.maximum = 50.0
    self.InterpResolutionSliderWidget.value = 25.0
    self.InterpResolutionSliderWidget.setToolTip("Number of interpolation points between control points. Default is 25.")
    parametersFormLayout.addRow("Resolution: ", self.InterpResolutionSliderWidget)

    #
    # Radio button for ring mode
    #
    self.RingLayout = qt.QHBoxLayout()
    self.RingOff = qt.QRadioButton("Off")
    self.RingOn = qt.QRadioButton("On")
    self.RingLayout.addWidget(self.RingOff)
    self.RingLayout.addWidget(self.RingOn)
    self.RingGroup = qt.QButtonGroup()
    self.RingGroup.addButton(self.RingOff)
    self.RingGroup.addButton(self.RingOn)

    parametersFormLayout.addRow("Ring mode: ", self.RingLayout)

    #
    # Check box to start curve visualization
    #
    self.EnableAutoUpdateCheckBox = qt.QCheckBox()
    self.EnableAutoUpdateCheckBox.checked = 0
    self.EnableAutoUpdateCheckBox.setToolTip("If checked, the CurveMaker module keeps updating the model as the points are updated.")
    parametersFormLayout.addRow("Auto update:", self.EnableAutoUpdateCheckBox)

    #
    # Button to generate a curve
    #
    self.GenerateButton = qt.QPushButton("Generate Curve")
    self.GenerateButton.toolTip = "Generate Curve"
    self.GenerateButton.enabled = True
    parametersFormLayout.addRow("", self.GenerateButton)
    
    # Connections
    self.InterpolationNone.connect('clicked(bool)', self.onSelectInterpolationNone)
    self.InterpolationCardinalSpline.connect('clicked(bool)', self.onSelectInterpolationCardinalSpline)
    self.InterpolationHermiteSpline.connect('clicked(bool)', self.onSelectInterpolationHermiteSpline)
    self.RingOff.connect('clicked(bool)', self.onRingOff)
    self.RingOn.connect('clicked(bool)', self.onRingOn)
    self.EnableAutoUpdateCheckBox.connect('toggled(bool)', self.onEnableAutoUpdate)
    self.SourceSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSourceSelected)
    self.DestinationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onDestinationSelected)
    self.RadiusSliderWidget.connect("valueChanged(double)", self.onTubeUpdated)
    self.InterpResolutionSliderWidget.connect("valueChanged(double)", self.onInterpResolutionUpdated)
    self.GenerateButton.connect('clicked(bool)', self.onGenerateCurve)

    # Set default
    ## default interpolation method
    self.InterpolationCardinalSpline.setChecked(True)
    self.onSelectInterpolationCardinalSpline(True)

    ## default ring mode
    self.RingOff.setChecked(True)
    self.onRingOff(True)

    
    #
    # Curve Length area
    #
    lengthCollapsibleButton = ctk.ctkCollapsibleButton()
    lengthCollapsibleButton.text = "Length"
    self.layout.addWidget(lengthCollapsibleButton)
    lengthFormLayout = qt.QFormLayout(lengthCollapsibleButton)
    lengthCollapsibleButton.collapsed = True

    #-- Curve length
    self.lengthLineEdit = qt.QLineEdit()
    self.lengthLineEdit.text = '--'
    self.lengthLineEdit.readOnly = True
    self.lengthLineEdit.frame = True
    self.lengthLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)

    lengthFormLayout.addRow("Curve Length (mm):", self.lengthLineEdit)

    #
    # Distance Area
    #
    distanceCollapsibleButton = ctk.ctkCollapsibleButton()
    distanceCollapsibleButton.text = "Distance"
    distanceCollapsibleButton.collapsed = True
    self.layout.addWidget(distanceCollapsibleButton)
    distanceFormLayout = qt.QFormLayout(distanceCollapsibleButton)

    #-- Point-to-curve distance

    #  - Markups selector for input points
    distanceLayout = qt.QVBoxLayout()

    self.targetFiducialsSelector = slicer.qMRMLNodeComboBox()
    self.targetFiducialsSelector.nodeTypes = ( ("vtkMRMLMarkupsFiducialNode"), "" )
    self.targetFiducialsSelector.selectNodeUponCreation = True
    self.targetFiducialsSelector.addEnabled = True
    self.targetFiducialsSelector.removeEnabled = True
    self.targetFiducialsSelector.noneEnabled = True
    self.targetFiducialsSelector.showHidden = False
    self.targetFiducialsSelector.showChildNodeTypes = False
    self.targetFiducialsSelector.setMRMLScene( slicer.mrmlScene )
    self.targetFiducialsSelector.setToolTip( "Select Markups for targets" )
    distanceLayout.addWidget(self.targetFiducialsSelector)

    self.targetFiducialsNode = None
    self.tagDestinationDispNode = None
    
    self.targetFiducialsSelector.connect("currentNodeChanged(vtkMRMLNode*)",
                                         self.onTargetFiducialsSelected)
      
    self.fiducialsTable = qt.QTableWidget(1, 3)
    self.fiducialsTable.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
    self.fiducialsTable.setSelectionMode(qt.QAbstractItemView.SingleSelection)
    self.fiducialsTableHeaders = ["Name", "Position (mm)", "Distance (mm)"]
    self.fiducialsTable.setHorizontalHeaderLabels(self.fiducialsTableHeaders)
    self.fiducialsTable.horizontalHeader().setStretchLastSection(True)
    distanceLayout.addWidget(self.fiducialsTable)

    self.extrapolateCheckBox = qt.QCheckBox()
    self.extrapolateCheckBox.checked = 0
    self.extrapolateCheckBox.setToolTip("Extrapolate the first and last segment to calculate the distance")
    self.extrapolateCheckBox.connect('toggled(bool)', self.updateTargetFiducialsTable)
    self.extrapolateCheckBox.text = 'Extrapolate curves to measure the distances'

    self.showErrorVectorCheckBox = qt.QCheckBox()
    self.showErrorVectorCheckBox.checked = 0
    self.showErrorVectorCheckBox.setToolTip("Show error vectors, which is defined by the target point and the closest point on the curve. The vector is perpendicular to the curve, unless the closest point is one end of the curve.")
    self.showErrorVectorCheckBox.connect('toggled(bool)', self.updateTargetFiducialsTable)
    self.showErrorVectorCheckBox.text = 'Show error vectors'

    distanceLayout.addWidget(self.extrapolateCheckBox)
    distanceLayout.addWidget(self.showErrorVectorCheckBox)
    distanceFormLayout.addRow("Distance from:", distanceLayout)

    #
    # Curvature Area
    #
    curvatureCollapsibleButton = ctk.ctkCollapsibleButton()
    curvatureCollapsibleButton.text = "Curvature"
    curvatureCollapsibleButton.collapsed = True 
    self.layout.addWidget(curvatureCollapsibleButton)
    curvatureFormLayout = qt.QFormLayout(curvatureCollapsibleButton)
    
    #-- Curvature
    self.curvatureLayout = qt.QHBoxLayout()
    self.curvatureOff = qt.QRadioButton("Off")
    self.curvatureOff.connect('clicked(bool)', self.onCurvatureOff)
    self.curvatureOn = qt.QRadioButton("On")
    self.curvatureOn.connect('clicked(bool)', self.onCurvatureOn)
    self.curvatureLayout.addWidget(self.curvatureOff)
    self.curvatureLayout.addWidget(self.curvatureOn)
    self.curvatureGroup = qt.QButtonGroup()
    self.curvatureGroup.addButton(self.curvatureOff)
    self.curvatureGroup.addButton(self.curvatureOn)

    curvatureFormLayout.addRow("Curvature mode:", self.curvatureLayout)

    self.autoCurvatureRangeLayout = qt.QHBoxLayout()
    self.autoCurvatureRangeOff = qt.QRadioButton("Manual")
    self.autoCurvatureRangeOff.connect('clicked(bool)', self.onAutoCurvatureRangeOff)
    self.autoCurvatureRangeOn = qt.QRadioButton("Auto")
    self.autoCurvatureRangeOn.connect('clicked(bool)', self.onAutoCurvatureRangeOn)
    self.autoCurvatureRangeLayout.addWidget(self.autoCurvatureRangeOff)
    self.autoCurvatureRangeLayout.addWidget(self.autoCurvatureRangeOn)
    self.autoCurvatureRangeGroup = qt.QButtonGroup()
    self.autoCurvatureRangeGroup.addButton(self.autoCurvatureRangeOff)
    self.autoCurvatureRangeGroup.addButton(self.autoCurvatureRangeOn)

    curvatureFormLayout.addRow("Color range:", self.autoCurvatureRangeLayout)

    #-- Color range
    self.curvatureColorRangeWidget = ctk.ctkRangeWidget()
    self.curvatureColorRangeWidget.setToolTip("Set color range")
    self.curvatureColorRangeWidget.setDecimals(3)
    self.curvatureColorRangeWidget.singleStep = 0.001
    self.curvatureColorRangeWidget.minimumValue = 0.0
    self.curvatureColorRangeWidget.maximumValue = 0.5
    self.curvatureColorRangeWidget.minimum = 0.0
    self.curvatureColorRangeWidget.maximum = 1.0
    curvatureFormLayout.addRow("Color range: ", self.curvatureColorRangeWidget)
    self.curvatureColorRangeWidget.connect('valuesChanged(double, double)', self.onUpdateCurvatureColorRange)

    #-- Curvature data
    self.meanCurvatureLineEdit = qt.QLineEdit()
    self.meanCurvatureLineEdit.text = '--'
    self.meanCurvatureLineEdit.readOnly = True
    self.meanCurvatureLineEdit.frame = True
    self.meanCurvatureLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.meanCurvatureLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    self.meanCurvatureLineEdit.enabled = False    
    curvatureFormLayout.addRow("Mean (mm^-1):", self.meanCurvatureLineEdit)

    self.minCurvatureLineEdit = qt.QLineEdit()
    self.minCurvatureLineEdit.text = '--'
    self.minCurvatureLineEdit.readOnly = True
    self.minCurvatureLineEdit.frame = True
    self.minCurvatureLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.minCurvatureLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    self.minCurvatureLineEdit.enabled = False
    curvatureFormLayout.addRow("Minimum (mm^-1):", self.minCurvatureLineEdit)

    self.maxCurvatureLineEdit = qt.QLineEdit()
    self.maxCurvatureLineEdit.text = '--'
    self.maxCurvatureLineEdit.readOnly = True
    self.maxCurvatureLineEdit.frame = True
    self.maxCurvatureLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.maxCurvatureLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    self.maxCurvatureLineEdit.enabled = False
    curvatureFormLayout.addRow("Maximum (mm^-1):", self.maxCurvatureLineEdit)

    ## Create a scale for curvature
    self.scalarBarWidget = vtk.vtkScalarBarWidget()
    actor = self.scalarBarWidget.GetScalarBarActor()
    actor.SetOrientationToVertical()
    actor.SetNumberOfLabels(11)
    actor.SetTitle("Curvature (mm^-1)")
    actor.SetLabelFormat(" %#8.3f")
    actor.SetPosition(0.1, 0.1)
    actor.SetWidth(0.1)
    actor.SetHeight(0.8)
    self.scalarBarWidget.SetEnabled(0)    
    
    layout = slicer.app.layoutManager()
    view = layout.threeDWidget(0).threeDView()
    renderer = layout.activeThreeDRenderer()
    self.scalarBarWidget.SetInteractor(renderer.GetRenderWindow().GetInteractor())
    self.lookupTable = vtk.vtkLookupTable()
    self.lookupTable.SetRange(0.0, 100.0)
    self.scalarBarWidget.GetScalarBarActor().SetLookupTable(self.lookupTable)

    ## default curvature mode: off
    self.curvatureOff.setChecked(True)
    self.onCurvatureOff(True)
    self.autoCurvatureRangeOff.setChecked(True)
    self.onAutoCurvatureRangeOff(True)
    
    # Add vertical spacer
    self.layout.addStretch(1)


  def cleanup(self):
    pass

  def onEnableAutoUpdate(self, state):
    self.logic.enableAutomaticUpdate(state)
    self.logic.updateCurve()


  def onGenerateCurve(self):
    self.logic.generateCurveOnce()
    
  def onSourceSelected(self):
    ## Remove observer if previous node exists
    #if self.logic.SourceNode and self.tagSourceNode:
    #  self.logic.SourceNode.RemoveObserver(self.tagSourceNode)

    # Update selected node, add observer, and update control points
    sourceNode = self.SourceSelector.currentNode()
    destinationNode = self.DestinationSelector.currentNode()
    if sourceNode:
      self.logic.CurrentSourceNode = sourceNode

      # Check if model has already been generated for this fiducial list
      tubeModelID = self.logic.CurrentSourceNode.GetAttribute('CurveMaker.CurveModel')
      self.DestinationSelector.setCurrentNodeID(tubeModelID)

    # Update AutoUpdate checkbox
    if sourceNode == None:
      self.EnableAutoUpdateCheckBox.setCheckState(False)
    else:
      if destinationNode == None:
        #self.logic.setSourceNodeObserver(sourceNode, 0)
        self.EnableAutoUpdateCheckBox.setCheckState(False)
      else:
        # Both source and destination are specified
        if sourceNode.GetAttribute('CurveMaker.AutoUpdate') == '1':
          self.EnableAutoUpdateCheckBox.setCheckState(True)
        else:
          self.EnableAutoUpdateCheckBox.setCheckState(False)

    self.logic.updateObservers()
    self.logic.updateCurve()

      
  def onDestinationSelected(self):
    if self.logic.CurrentDestinationNode and self.tagDestinationNode:
      self.logic.CurrentDestinationNode.RemoveObserver(self.tagDestinationNode)
      if self.logic.CurrentDestinationNode.GetDisplayNode() and self.tagDestinationDispNode:
        self.logic.CurrentDestinationNode.GetDisplayNode().RemoveObserver(self.tagDestinationDispNode)
    
    # Update destination node
    if self.DestinationSelector.currentNode():
      self.logic.CurrentDestinationNode = self.DestinationSelector.currentNode()
      self.tagDestinationNode = self.logic.CurrentDestinationNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onModelModifiedEvent)

      if self.logic.CurrentDestinationNode.GetDisplayNode():
        self.tagDestinationDispNode = self.logic.CurrentDestinationNode.GetDisplayNode().AddObserver(vtk.vtkCommand.ModifiedEvent, self.onModelDisplayModifiedEvent)

    # Update checkbox
    sourceNode = self.SourceSelector.currentNode()
    destinationNode = self.DestinationSelector.currentNode()
    if sourceNode == None:
      self.EnableAutoUpdateCheckBox.setCheckState(False)
      
    if destinationNode == None:
      self.EnableAutoUpdateCheckBox.setCheckState(False)
      if sourceNode != None:
        self.logic.setSourceNodeObserver(sourceNode, False)

    # Set CurveMake.CurveModel attribute
    if destinationNode and destinationNode:
      self.logic.CurrentSourceNode.SetAttribute('CurveMaker.CurveModel',self.logic.CurrentDestinationNode.GetID())
      self.logic.updateCurve()

      
  def onTubeUpdated(self):
    self.logic.setTubeRadius(self.RadiusSliderWidget.value)
    self.logic.updateCurve()

    
  def onInterpResolutionUpdated(self):
    self.logic.setInterpResolution(self.InterpResolutionSliderWidget.value)

    
  def onReload(self,moduleName="CurveMaker"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)

    
  def onSelectInterpolationNone(self, s):
    self.logic.setInterpolationMethod('none')
    self.InterpResolutionSliderWidget.enabled = True
    if self.RingOn != None:
      self.RingOn.enabled = True
    self.logic.updateCurve()

      
  def onSelectInterpolationCardinalSpline(self, s):
    self.logic.setInterpolationMethod('cardinal')
    self.InterpResolutionSliderWidget.enabled = True
    if self.RingOn != None:
      self.RingOn.enabled = True
    self.logic.updateCurve()

      
  def onSelectInterpolationHermiteSpline(self, s):
    self.logic.setInterpolationMethod('hermite')
    self.InterpResolutionSliderWidget.enabled = False
    ## Currently Hermite Spline Interpolation does not support the ring mode 
    if self.RingOn != None and self.RingOff != None:
      self.RingOn.checked = False
      self.logic.setRing(0)
      self.RingOn.enabled = False
      self.RingOff.checked = True
    self.logic.updateCurve()

      
  def onRingOff(self, s):
    self.logic.setRing(0)

    
  def onRingOn(self, s):
    self.logic.setRing(1)

    
  def onCurvatureOff(self, s):
    self.logic.setCurvature(0)
    self.scalarBarWidget.SetEnabled(0)
    if self.logic.CurrentDestinationNode:
      dispNode = self.logic.CurrentDestinationNode.GetDisplayNode()
      dispNode.ScalarVisibilityOff()
    self.meanCurvatureLineEdit.enabled = False
    self.minCurvatureLineEdit.enabled = False
    self.maxCurvatureLineEdit.enabled = False
    self.meanCurvatureLineEdit.text = '--'
    self.minCurvatureLineEdit.text = '--'
    self.maxCurvatureLineEdit.text = '--'
    self.logic.updateCurve()
    
    
  def onCurvatureOn(self, s):
    self.logic.setCurvature(1)
    self.scalarBarWidget.Modified()
    self.scalarBarWidget.SetEnabled(1)
    if self.logic.CurrentDestinationNode:
      dispNode = self.logic.CurrentDestinationNode.GetDisplayNode()
      colorTable = slicer.util.getNode('ColdToHotRainbow')
      dispNode.SetAndObserveColorNodeID(colorTable.GetID())
      dispNode.ScalarVisibilityOn()
      dispNode.SetScalarRangeFlag(slicer.vtkMRMLModelDisplayNode.UseDisplayNodeScalarRange)
      self.scalarBarWidget.GetScalarBarActor().SetLookupTable(colorTable.GetLookupTable())
    self.meanCurvatureLineEdit.enabled = True
    self.minCurvatureLineEdit.enabled = True
    self.maxCurvatureLineEdit.enabled = True
    #self.logic.updateCurve()
    self.logic.generateCurveOnce()

    
  def onAutoCurvatureRangeOff(self, s):
    self.curvatureColorRangeWidget.enabled = True
    if self.logic.CurrentDestinationNode:
      dispNode = self.logic.CurrentDestinationNode.GetDisplayNode()
      if dispNode:
        dispNode.AutoScalarRangeOff()

    
  def onAutoCurvatureRangeOn(self, s):
    self.curvatureColorRangeWidget.enabled = False
    if self.logic.CurrentDestinationNode:
      dispNode = self.logic.CurrentDestinationNode.GetDisplayNode()
      if dispNode:
        dispNode.AutoScalarRangeOn()
        self.updateCurvatureInterface()
    
  def onUpdateCurvatureColorRange(self, min, max):
    if self.logic.CurrentDestinationNode:
      dispNode = self.logic.CurrentDestinationNode.GetDisplayNode()
      if dispNode:
        if self.autoCurvatureRangeOff.checked == True:
          dispNode.AutoScalarRangeOff()
        dispNode.SetScalarRange(min, max)
        dispNode.Modified()

    
  def onModelModifiedEvent(self, caller, event):
    self.lengthLineEdit.text = '%.2f' % self.logic.CurveLength
    self.updateTargetFiducialsTable()
    self.updateCurvatureInterface()

        
  def onModelDisplayModifiedEvent(self, caller, event):
    self.updateCurvatureInterface()


  def updateCurvatureInterface(self):
    if self.logic.CurrentDestinationNode and self.logic.Curvature:
      dispNode = self.logic.CurrentDestinationNode.GetDisplayNode()
      if dispNode:
        colorTable = dispNode.GetColorNode()
        if colorTable == None:
          colorTable = slicer.util.getNode('ColdToHotRainbow')
          dispNode.SetAndObserveColorNodeID(colorTable.GetID())
        self.scalarBarWidget.GetScalarBarActor().SetLookupTable(colorTable.GetLookupTable())
        srange = dispNode.GetScalarRange()
        lut2 = self.scalarBarWidget.GetScalarBarActor().GetLookupTable()
        lut2.SetRange(srange[0], srange[1])
        summary = self.logic.getCurvatureSummary()
        if summary != None:
          self.meanCurvatureLineEdit.text = '%.6f' % summary['mean']
          self.minCurvatureLineEdit.text = '%.6f' % summary['min']
          self.maxCurvatureLineEdit.text = '%.6f' % summary['max']
        srange = dispNode.GetScalarRange()
        if srange[0] != self.curvatureColorRangeWidget.minimumValue:
          self.curvatureColorRangeWidget.minimumValue = srange[0]
        if srange[1] != self.curvatureColorRangeWidget.maximumValue:
          self.curvatureColorRangeWidget.maximumValue = srange[1]
    
    
  def onTargetFiducialsSelected(self):

    # Remove observer if previous node exists
    if self.targetFiducialsNode and self.tag:
      self.targetFiducialsNode.RemoveObserver(self.tag)

    # Update selected node, add observer, and update control points
    if self.targetFiducialsSelector.currentNode():
      self.targetFiducialsNode = self.targetFiducialsSelector.currentNode()
      self.tag = self.targetFiducialsNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onTargetFiducialsUpdated, 2)
    else:
      self.targetFiducialsNode = None
      self.tag = None
    self.updateTargetFiducialsTable()

    
  def onTargetFiducialsUpdated(self,caller,event):
    self.updateTargetFiducialsTable()

      
  def updateTargetFiducialsTable(self):

    if not self.targetFiducialsNode:
      self.fiducialsTable.clear()
      self.fiducialsTable.setHorizontalHeaderLabels(self.fiducialsTableHeaders)
      
    else:
      
      extrapolate = self.extrapolateCheckBox.isChecked()
      showErrorVec = self.showErrorVectorCheckBox.isChecked()
      
      self.fiducialsTableData = []
      nOfControlPoints = self.targetFiducialsNode.GetNumberOfFiducials()

      if self.fiducialsTable.rowCount != nOfControlPoints:
        self.fiducialsTable.setRowCount(nOfControlPoints)

      dist = ''
      for i in range(nOfControlPoints):

        label = self.targetFiducialsNode.GetNthFiducialLabel(i)
        pos = [0.0, 0.0, 0.0]

        self.targetFiducialsNode.GetNthFiducialPosition(i,pos)
        (err, evec) = self.logic.distanceToPoint(pos, extrapolate)

        posstr = '(%.3f, %.3f, %.3f)' % (pos[0], pos[1], pos[2])
        if showErrorVec:
          dist =   '%.3f (%.3f, %.3f, %.3f)' %  (err, evec[0], evec[1], evec[2])
        else:
          dist =   '%.3f' %  err

        cellLabel = qt.QTableWidgetItem(label)
        cellPosition = qt.QTableWidgetItem(posstr)
        cellDistance = qt.QTableWidgetItem(dist)
        row = [cellLabel, cellPosition, cellDistance]

        self.fiducialsTable.setItem(i, 0, row[0])
        self.fiducialsTable.setItem(i, 1, row[1])
        self.fiducialsTable.setItem(i, 2, row[2])
        self.fiducialsTableData.append(row)
        
    self.fiducialsTable.show()
    

#
# CurveMakerLogic
#

class CurveMakerLogic:

  def __init__(self):
    self.CurrentSourceNode = None
    self.CurrentDestinationNode = None

    self.AutomaticUpdate = False
    self.NumberOfIntermediatePoints = 20
    self.ModelColor = [0.0, 0.0, 1.0]

    self.CurvePoly = dict()
    
    # Interpolation method:
    #  'none': None
    #  'cardinal': Cardinal Spline (VTK default)
    #  'hermite': Hermite Spline (Endoscopy module default)
    self.DefaultInterpolationMethod = 'cardinal'
    self.DefaultRingMode = 0
    self.DefaultInterpResolution = 25
    self.DefaultTubeRadius = 5.0
    
    self.CurveLength = -1.0  ## Length of the curve (<0 means 'not measured')
    self.Curvature = 0
    self.curvatureMeanKappa = None
    self.curvatureMinKappa = None
    self.curvatureMaxKappa = None

  def setNumberOfIntermediatePoints(self,npts):
    if npts > 0:
      self.NumberOfIntermediatePoints = npts
    self.updateCurve()

  def setTubeRadius(self, radius, sourceNode=None):
    #self.TubeRadius = radius
    if sourceNode == None:
      if self.CurrentSourceNode:
        self.CurrentSourceNode.SetAttribute('CurveMaker.TubeRadius', str(radius))
    else:
      sourceNode.SetAttribute('CurveMaker.TubeRadius', str(radius))

  def setInterpolationMethod(self, method, sourceNode=None):
    if sourceNode == None:
      if self.CurrentSourceNode:
        if method == 'cardinal' or method == 'hermite':
          self.CurrentSourceNode.SetAttribute('CurveMaker.InterpolationMethod', method)
        else:
          self.CurrentSourceNode.SetAttribute('CurveMaker.InterpolationMethod', 'none')
    else:
      if method == 'cardinal' or method == 'hermite':
        sourceNode.SetAttribute('CurveMaker.InterpolationMethod', method)
      else:
        sourceNode.SetAttribute('CurveMaker.InterpolationMethod', 'none')
        
  def setRing(self, switch):
    #self.RingMode = switch
    if self.CurrentSourceNode:
      self.CurrentSourceNode.SetAttribute('CurveMaker.RingMode', str(switch))
    self.updateCurve()

  def setCurvature(self, switch):
    self.Curvature = switch
    self.updateCurve()

  def setInterpResolution(self, res):
    ## Resoution is specified as the number of interpolation points between two consecutive control points
    #self.interpResolution = res
    if self.CurrentSourceNode:
      self.CurrentSourceNode.SetAttribute('CurveMaker.InterpolationResolution', str(res))
    self.updateCurve()
    
  def enableAutomaticUpdate(self, auto, sourceNode=None):
    if sourceNode == None:
      self.setSourceNodeObserver(self.CurrentSourceNode, auto)
    else:
      self.setSourceNodeObserver(sourceNode, auto)

  def generateCurveOnce(self):
    #prevAutomaticUpdate = self.AutomaticUpdate
    #self.AutomaticUpdate = True
    self.updateCurve(currentOnly=True)
    #self.AutomaticUpdate = prevAutomaticUpdate

  def setSourceNodeObserver(self, fnode, switch):
    if fnode == None:
      return

    if switch == True:
      fnode.SetAttribute('CurveMaker.AutoUpdate', '1')
      if fnode.GetAttribute('CurveMaker.ObserverTag') == None:
        # If there is no observer added despite the active AutoUpdate status
        # TODO: slicer.vtkMRMLMarkupsNode.PointModifiedEvent is not called when a new point is added on Slicer 4.8
        tag = fnode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.controlPointsUpdated, 2)
        fnode.SetAttribute('CurveMaker.ObserverTag', str(tag))
      fnode.SetAttribute('CurveMaker.AutoUpdate', '1')
    else:
      tag = fnode.GetAttribute('CurveMaker.ObserverTag')
      if tag != None:
        # if there is an observer
        fnode.RemoveObserver(int(tag))
        fnode.SetAttribute('CurveMaker.ObserverTag', None)
      fnode.SetAttribute('CurveMaker.AutoUpdate', '0')
    
  def updateObservers(self):
    ## Scan the scene and add/remove observers based on the flag attribute
    fnodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLMarkupsFiducialNode')
    
    for i in range(fnodes.GetNumberOfItems()):
      fnode = fnodes.GetItemAsObject(i)
      if fnode.GetAttribute('CurveMaker.AutoUpdate') == '1':
        self.setSourceNodeObserver(fnode, True)
      else:
        self.setSourceNodeObserver(fnode, False)
        
  def controlPointsUpdated(self,caller,event):
    self.updateCurve()

  def nodeToPoly(self, sourceNode, outputPoly, closed=False):
    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()

    nOfControlPoints = sourceNode.GetNumberOfFiducials()
    pos = [0.0, 0.0, 0.0]
    posStartEnd = [0.0, 0.0, 0.0]

    offset = 0
    
    if not closed:
      points.SetNumberOfPoints(nOfControlPoints)
      cellArray.InsertNextCell(nOfControlPoints)
    else:
      posStart = [0.0, 0.0, 0.0]
      posEnd = [0.0, 0.0, 0.0]
      sourceNode.GetNthFiducialPosition(0,posStart)
      sourceNode.GetNthFiducialPosition(nOfControlPoints-1,posEnd)
      posStartEnd[0] = (posStart[0]+posEnd[0])/2.0
      posStartEnd[1] = (posStart[1]+posEnd[1])/2.0
      posStartEnd[2] = (posStart[2]+posEnd[2])/2.0
      points.SetNumberOfPoints(nOfControlPoints+2)
      cellArray.InsertNextCell(nOfControlPoints+2)

      points.SetPoint(0,posStartEnd)
      cellArray.InsertCellPoint(0)

      offset = 1
      
    for i in range(nOfControlPoints):
      sourceNode.GetNthFiducialPosition(i,pos)
      points.SetPoint(offset+i,pos)
      cellArray.InsertCellPoint(offset+i)

    offset = offset + nOfControlPoints
    
    if closed:
      points.SetPoint(offset,posStartEnd)
      cellArray.InsertCellPoint(offset)

    outputPoly.Initialize()
    outputPoly.SetPoints(points)
    outputPoly.SetLines(cellArray)

  def nodeToPolyCardinalSpline(self, sourceNode, outputPoly, closed=False):

    nOfControlPoints = sourceNode.GetNumberOfFiducials()
    pos = [0.0, 0.0, 0.0]

    # One spline for each direction.
    aSplineX = vtk.vtkCardinalSpline()
    aSplineY = vtk.vtkCardinalSpline()
    aSplineZ = vtk.vtkCardinalSpline()

    if closed:
      aSplineX.ClosedOn()
      aSplineY.ClosedOn()
      aSplineZ.ClosedOn()
    else:
      aSplineX.ClosedOff()
      aSplineY.ClosedOff()
      aSplineZ.ClosedOff()

    for i in range(0, nOfControlPoints):
      sourceNode.GetNthFiducialPosition(i, pos)
      aSplineX.AddPoint(i, pos[0])
      aSplineY.AddPoint(i, pos[1])
      aSplineZ.AddPoint(i, pos[2])
    
    # Interpolate x, y and z by using the three spline filters and
    # create new points
    interpResolutionStr = sourceNode.GetAttribute('CurveMaker.InterpolationResolution')
    interpResolution = self.DefaultInterpResolution
    if interpResolutionStr:
      interpResolution = float(interpResolutionStr)
    nInterpolatedPoints = (interpResolution+2)*(nOfControlPoints-1) # One section is devided into self.interpResolution segments
    points = vtk.vtkPoints()
    r = [0.0, 0.0]
    aSplineX.GetParametricRange(r)
    t = r[0]
    p = 0
    tStep = (nOfControlPoints-1.0)/(nInterpolatedPoints-1.0)
    nOutputPoints = 0

    if closed:
      while t < r[1]+1.0:
        points.InsertPoint(p, aSplineX.Evaluate(t), aSplineY.Evaluate(t), aSplineZ.Evaluate(t))
        t = t + tStep
        p = p + 1
      ## Make sure to close the loop
      points.InsertPoint(p, aSplineX.Evaluate(r[0]), aSplineY.Evaluate(r[0]), aSplineZ.Evaluate(r[0]))
      p = p + 1
      points.InsertPoint(p, aSplineX.Evaluate(r[0]+tStep), aSplineY.Evaluate(r[0]+tStep), aSplineZ.Evaluate(r[0]+tStep))
      nOutputPoints = p + 1
    else:
      while t < r[1]:
        points.InsertPoint(p, aSplineX.Evaluate(t), aSplineY.Evaluate(t), aSplineZ.Evaluate(t))
        t = t + tStep
        p = p + 1
      nOutputPoints = p
    
    lines = vtk.vtkCellArray()
    lines.InsertNextCell(nOutputPoints)
    for i in range(0, nOutputPoints):
      lines.InsertCellPoint(i)
        
    outputPoly.SetPoints(points)
    outputPoly.SetLines(lines)

  def pathToPoly(self, path, poly):
    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()

    points = vtk.vtkPoints()
    poly.SetPoints(points)

    lines = vtk.vtkCellArray()
    poly.SetLines(lines)

    linesIDArray = lines.GetData()
    linesIDArray.Reset()
    linesIDArray.InsertNextTuple1(0)
    
    polygons = vtk.vtkCellArray()
    poly.SetPolys( polygons )
    idArray = polygons.GetData()
    idArray.Reset()
    idArray.InsertNextTuple1(0)
    
    for point in path:
      pointIndex = points.InsertNextPoint(*point)
      linesIDArray.InsertNextTuple1(pointIndex)
      linesIDArray.SetTuple1( 0, linesIDArray.GetNumberOfTuples() - 1 )
      lines.SetNumberOfCells(1)


  def nodeToPolyHermiteSpline(self, sourceNode, outputPoly, closed=False):
    endoscopyResult = EndoscopyComputePath(sourceNode)
    self.pathToPoly(endoscopyResult.path, outputPoly)


  def calculateLineLength(self, poly):
    lines = poly.GetLines()
    points = poly.GetPoints()
    pts = vtk.vtkIdList()

    lines.GetCell(0, pts)
    ip = numpy.array(points.GetPoint(pts.GetId(0)))
    n = pts.GetNumberOfIds()

    # Check if there is overlap between the first and last segments
    # (for making sure to close the loop for spline curves)
    if n > 2:
      slp = numpy.array(points.GetPoint(pts.GetId(n-2)))
      # Check distance between the first point and the second last point
      if numpy.linalg.norm(slp-ip) < 0.00001:
        n = n - 1
        
    length = 0.0
    pp = ip
    for i in range(1,n):
      p = numpy.array(points.GetPoint(pts.GetId(i)))
      length = length + numpy.linalg.norm(pp-p)
      pp = p

    return length


  def computeCurvatures(self, poly, curvatureValues):
    # Calculate point-by-point curvature of the curve
    # Returns mean/min/max curvature
    
    lines = poly.GetLines()
    points = poly.GetPoints()
    pts = vtk.vtkIdList()

    lines.GetCell(0, pts)
    ip = numpy.array(points.GetPoint(pts.GetId(0)))
    n = pts.GetNumberOfIds()

    ## Check if there is overlap between the first and last segments
    ## (for making sure to close the loop for spline curves)
    #if n > 2:
    #  slp = numpy.array(points.GetPoint(pts.GetId(n-2)))
    #  # Check distance between the first point and the second last point
    #  if numpy.linalg.norm(slp-ip) < 0.00001:
    #    n = n - 1

    curvatureValues.Initialize()
    curvatureValues.SetName("Curvature")
    curvatureValues.SetNumberOfComponents(1)
    curvatureValues.SetNumberOfTuples(n)
    curvatureValues.Reset()
    curvatureValues.FillComponent(0,0.0)  

    minKappa = 0.0
    maxKappa = 0.0
    meanKappa = 0.0   # NOTE: mean is weighted by the lengh of each segment
    
    pp = numpy.array(points.GetPoint(pts.GetId(0)))
    p  = numpy.array(points.GetPoint(pts.GetId(1)))
    ds = numpy.linalg.norm(p-pp)
    pT = (p-pp) / ds
    pp = p
    pm = (p+pp)/2.0
    length = 0.0 + numpy.linalg.norm(pm-pp)
    
    curvatureValues.InsertValue(pts.GetId(0), 0.0) # The curvature for the first cell is 0.0

    for i in range(1,n-1):
      p = numpy.array(points.GetPoint(pts.GetId(i+1)))
      ds = numpy.linalg.norm(p-pp)
      T  = (p-pp) / ds
      kappa = numpy.linalg.norm(T-pT) / ds # Curvature
      curvatureValues.InsertValue(pts.GetId(i), kappa) # The curvature for the first cell is 0.0

      m = (p+pp)/2.0 
      l = numpy.linalg.norm(m-pm) # length for this segment
      if kappa < minKappa:
        minKappa = kappa
      elif kappa > maxKappa:
        maxKappa = kappa
      meanKappa = meanKappa + kappa * l  # weighted mean
      length = length + l

      pp = p
      pm = m
      pT = T

    curvatureValues.InsertValue(pts.GetId(n-1), 0.0) # The curvature for the last cell is 0.0
    
    length = length + numpy.linalg.norm(pp-pm)
          
    meanKappa = meanKappa / length
    
    # TODO: This routin does not consider a closed loop. If a closed loop is specified,
    # It needs to calculate the curveture of two ends differently.

    return (meanKappa, minKappa, maxKappa)

  
  def updateCurve(self, currentOnly=False):

    #if self.AutomaticUpdate == False:
    #  return
    if currentOnly:
      self.updateSingleCurve(self.CurrentSourceNode, False)
    else:
      fnodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLMarkupsFiducialNode')
      for i in range(fnodes.GetNumberOfItems()):
        fnode = fnodes.GetItemAsObject(i)
        self.updateSingleCurve(fnode, True)
      

  def updateSingleCurve(self, sourceNode, autoUpdate):

    destinationNode = None
    fUpdate = True
    
    if sourceNode:
      nodeID = sourceNode.GetAttribute('CurveMaker.CurveModel')
      if nodeID != None:
        destinationNode = slicer.mrmlScene.GetNodeByID(nodeID)
      if autoUpdate:
        fUpdate = (sourceNode.GetAttribute('CurveMaker.AutoUpdate') == '1')
      
    if sourceNode and destinationNode and fUpdate:

      if sourceNode.GetNumberOfFiducials() < 2:
        if sourceNode.GetID() in self.CurvePoly:
          if self.CurvePoly[sourceNode.GetID()] != None:
            self.CurvePoly[sourceNode.GetID()].Initialize()
        self.CurveLength = 0.0

      else:
        if not (sourceNode.GetID() in self.CurvePoly) or self.CurvePoly[sourceNode.GetID()] == None:
          self.CurvePoly[sourceNode.GetID()] = vtk.vtkPolyData()
        
        if destinationNode.GetDisplayNodeID() == None:
          modelDisplayNode = slicer.vtkMRMLModelDisplayNode()
          modelDisplayNode.SetColor(self.ModelColor)
          slicer.mrmlScene.AddNode(modelDisplayNode)
          destinationNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

        method = self.DefaultInterpolationMethod
        methodStr = sourceNode.GetAttribute('CurveMaker.InterpolationMethod')
        if methodStr:
          method = methodStr

        ringMode = self.DefaultRingMode
        ringModeStr = sourceNode.GetAttribute('CurveMaker.RingMode')
        if ringModeStr:
          ringMode = int(ringModeStr)

        if method == 'none' or method == None:
          if ringMode > 0:
            self.nodeToPoly(sourceNode, self.CurvePoly[sourceNode.GetID()], True)
          else:
            self.nodeToPoly(sourceNode, self.CurvePoly[sourceNode.GetID()], False)
        
        elif method == 'cardinal': # Cardinal Spline
        
          if ringMode > 0:
            self.nodeToPolyCardinalSpline(sourceNode, self.CurvePoly[sourceNode.GetID()], True)
          else:
            self.nodeToPolyCardinalSpline(sourceNode, self.CurvePoly[sourceNode.GetID()], False)
        
        elif method == 'hermite': # Hermite Spline
        
          if ringMode > 0:        
            self.nodeToPolyHermiteSpline(sourceNode, self.CurvePoly[sourceNode.GetID()], True)
          else:
            self.nodeToPolyHermiteSpline(sourceNode, self.CurvePoly[sourceNode.GetID()], False)
          
        self.CurveLength = self.calculateLineLength(self.CurvePoly[sourceNode.GetID()])

      tubeFilter = vtk.vtkTubeFilter()
      curvatureValues = vtk.vtkDoubleArray()

      fCurvature = False
      if self.CurrentSourceNode:
        fCurvature = (sourceNode.GetID() == self.CurrentSourceNode.GetID() and self.Curvature)

      if fCurvature:
        ## If the curvature option is ON, calculate the curvature along the curve.
        (meanKappa, minKappa, maxKappa) = self.computeCurvatures(self.CurvePoly[sourceNode.GetID()], curvatureValues)
        self.CurvePoly[sourceNode.GetID()].GetPointData().AddArray(curvatureValues)
        self.curvatureMeanKappa = meanKappa
        self.curvatureMinKappa = minKappa
        self.curvatureMaxKappa = maxKappa
      else:
        self.curvatureMeanKappa = None
        self.curvatureMinKappa = None
        self.curvatureMaxKappa = None

      if (sourceNode.GetID() in self.CurvePoly) and self.CurvePoly[sourceNode.GetID()]:
        tubeFilter.SetInputData(self.CurvePoly[sourceNode.GetID()])
        radius = sourceNode.GetAttribute('CurveMaker.TubeRadius')
        if radius:
          tubeFilter.SetRadius(float(radius))
        else:
          tubeFilter.SetRadius(self.DefaultTubeRadius)
        tubeFilter.SetNumberOfSides(20)
        tubeFilter.CappingOn()
        tubeFilter.Update()

      destinationNode.SetAndObservePolyData(tubeFilter.GetOutput())
      destinationNode.Modified()
      
      if destinationNode.GetScene() == None:
        slicer.mrmlScene.AddNode(destinationNode)

      displayNode = destinationNode.GetDisplayNode()
      if displayNode:
        if fCurvature:
          displayNode.SetActiveScalarName('Curvature')
        else:
          displayNode.SetActiveScalarName('')
        
        
  def getCurvatureSummary(self):

    if self.Curvature:
      summary = {}
      summary['mean'] = self.curvatureMeanKappa
      summary['min'] = self.curvatureMinKappa
      summary['max'] = self.curvatureMaxKappa
      return summary
    else:
      return None
    

  def distanceToPoint(self, point, extrapolate):

    # distanceToPoint() calculates the approximate minimum distance between
    # the specified point and the closest segment of the curve.
    # It calculates the minimum distance between the point and each segment
    # of the curve (approxmated as a straight line) and select the segment with
    # the minimum distance from the point as a closest segment.

    npoint = numpy.array(point)

    if self.CurvePoly[self.CurrentSourceNode.GetID()] == None:
      return numpy.Inf

    lines = self.CurvePoly[self.CurrentSourceNode.GetID()].GetLines()
    points = self.CurvePoly[self.CurrentSourceNode.GetID()].GetPoints()
    pts = vtk.vtkIdList()

    lines.GetCell(0, pts)
    ip = numpy.array(points.GetPoint(pts.GetId(0)))
    n = pts.GetNumberOfIds()

    # First point on the segment
    p1 = ip

    minMag2 = numpy.Inf
    minIndex = -1
    minErrVec = numpy.array([0.0, 0.0, 0.0])

    errVec = numpy.array([0.0, 0.0, 0.0])
    for i in range(1,n):
      # Second point on the segment
      p2 = numpy.array(points.GetPoint(pts.GetId(i)))

      # Normal vector along the segment
      nvec = p2-p1
      norm = numpy.linalg.norm(nvec)
      if norm != 0:
        nnvec = nvec / norm

      # Calculate the distance between the point and the segment
      mag2 = 0.0

      op = npoint - p1
      aproj = numpy.inner(op, nnvec)

      if extrapolate and ((i == 1 and aproj < 0.0) or (i == n-1 and aproj > 0.0)):
        # extrapolate first or last segment
        errVec = op-aproj*nnvec  # perpendicular
        mag2 = numpy.inner(errVec,errVec) # magnitude^2
      else:
        if aproj < 0.0:
          errVec = npoint - p1
          mag2 = numpy.inner(errVec, errVec) # magnitude^2
        elif aproj > norm:
          errVec = npoint - p2
          mag2 = numpy.inner(errVec, errVec) # magnitude^2
        else:
          errVec = op-aproj*nnvec # perpendicular
          mag2 = numpy.inner(errVec,errVec) # magnitude^2
        
      if mag2 < minMag2:
        minMag2 = mag2
        minIndex = i
        minErrVec = errVec
    
      p1 = p2

    distance = numpy.sqrt(minMag2)

    return (distance, minErrVec)

