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
    self.RingOff = None
    self.RingOn = None
    
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
    parametersFormLayout.addRow("Radius: ", self.RadiusSliderWidget)

    #
    # Radio button to select interpolation method
    #
    self.InterpolationLayout = qt.QHBoxLayout()
    self.InterpolationNone = qt.QRadioButton("None")
    self.InterpolationNone.connect('clicked(bool)', self.onSelectInterpolationNone)
    self.InterpolationCardinalSpline = qt.QRadioButton("Cardinal Spline")
    self.InterpolationCardinalSpline.connect('clicked(bool)', self.onSelectInterpolationCardinalSpline)
    self.InterpolationHermiteSpline = qt.QRadioButton("Hermite Spline (for Endoscopy)")
    self.InterpolationHermiteSpline.connect('clicked(bool)', self.onSelectInterpolationHermiteSpline)
    self.InterpolationLayout.addWidget(self.InterpolationNone)
    self.InterpolationLayout.addWidget(self.InterpolationCardinalSpline)
    self.InterpolationLayout.addWidget(self.InterpolationHermiteSpline)
    
    self.InterpolationGroup = qt.QButtonGroup()
    self.InterpolationGroup.addButton(self.InterpolationNone)
    self.InterpolationGroup.addButton(self.InterpolationCardinalSpline)
    self.InterpolationGroup.addButton(self.InterpolationHermiteSpline)

    ## default interpolation method
    self.InterpolationCardinalSpline.setChecked(True)
    self.onSelectInterpolationCardinalSpline(True)

    parametersFormLayout.addRow("Interpolation: ", self.InterpolationLayout)

    #
    # Radio button for ring mode
    #
    self.RingLayout = qt.QHBoxLayout()
    self.RingOff = qt.QRadioButton("Off")
    self.RingOff.connect('clicked(bool)', self.onRingOff)
    self.RingOn = qt.QRadioButton("On")
    self.RingOn.connect('clicked(bool)', self.onRingOn)
    self.RingLayout.addWidget(self.RingOff)
    self.RingLayout.addWidget(self.RingOn)
    
    self.RingGroup = qt.QButtonGroup()
    self.RingGroup.addButton(self.RingOff)
    self.RingGroup.addButton(self.RingOn)

    ## default ring mode
    self.RingOff.setChecked(True)
    self.onRingOff(True)

    parametersFormLayout.addRow("Ring mode: ", self.RingLayout)
    
    #
    # Check box to start curve visualization
    #
    self.EnableCheckBox = qt.QCheckBox()
    self.EnableCheckBox.checked = 0
    self.EnableCheckBox.setToolTip("If checked, the CurveMaker module keeps updating the model as the points are updated.")
    parametersFormLayout.addRow("Enable", self.EnableCheckBox)

    # Connections
    self.EnableCheckBox.connect('toggled(bool)', self.onEnable)
    self.SourceSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSourceSelected)
    self.DestinationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onDestinationSelected)
    self.RadiusSliderWidget.connect("valueChanged(double)", self.onTubeUpdated)


    #
    # Measurements Area
    #
    measurementsCollapsibleButton = ctk.ctkCollapsibleButton()
    measurementsCollapsibleButton.text = "Measurements"
    self.layout.addWidget(measurementsCollapsibleButton)

    # Layout within the dummy collapsible button
    measurementsFormLayout = qt.QFormLayout(measurementsCollapsibleButton)

    self.lengthLineEdit = qt.QLineEdit()
    self.lengthLineEdit.text = '--'
    self.lengthLineEdit.readOnly = True
    self.lengthLineEdit.frame = True
    self.lengthLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)

    lengthUnitLabel = qt.QLabel('mm')

    lengthLayout = qt.QHBoxLayout()
    lengthLayout.addWidget(self.lengthLineEdit)
    lengthLayout.addWidget(lengthUnitLabel)

    measurementsFormLayout.addRow("Curve length:", lengthLayout)

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
      #self.logic.generateControlPolyData()
      self.logic.updateCurve()

  def onDestinationSelected(self):
    # Update destination node
    if self.DestinationSelector.currentNode():
      self.logic.DestinationNode = self.DestinationSelector.currentNode()
      self.logic.DestinationNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onModelModifiedEvent)
      ## TODO: Need to remove observer?


    # Update checkbox
    if (self.SourceSelector.currentNode() == None or self.DestinationSelector.currentNode() == None):
      self.EnableCheckBox.setCheckState(False)
    else:
      self.logic.SourceNode.SetAttribute('CurveMaker.CurveModel',self.logic.DestinationNode.GetID())
      #self.logic.generateControlPolyData()
      self.logic.updateCurve()



  def onTubeUpdated(self):
    self.logic.setTubeRadius(self.RadiusSliderWidget.value)

  def onReload(self,moduleName="CurveMaker"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)

  def onSelectInterpolationNone(self, s):
    self.logic.setInterpolationMethod(0)
    if self.RingOn != None:
      self.RingOn.enabled = True

  def onSelectInterpolationCardinalSpline(self, s):
    self.logic.setInterpolationMethod(1)
    if self.RingOn != None:
      self.RingOn.enabled = True
    
  def onSelectInterpolationHermiteSpline(self, s):
    self.logic.setInterpolationMethod(2)
    ## Currently Hermite Spline Interpolation does not support the ring mode 
    if self.RingOn != None and self.RingOff != None:
      self.RingOn.checked = False
      self.logic.setRing(0)
      self.RingOn.enabled = False
      self.RingOff.checked = True

  def onRingOff(self, s):
    self.logic.setRing(0)

  def onRingOn(self, s):
    self.logic.setRing(1)

  def onModelModifiedEvent(self, caller, event):
    self.lengthLineEdit.text = '%.2f' % self.logic.CurveLength


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

    self.CurvePoly = None
    
    # Interpolation method:
    #  0: None
    #  1: Cardinal Spline (VTK default)
    #  2: Hermite Spline (Endoscopy module default)
    self.InterpolationMethod = 0

    self.RingMode = 0
    self.CurveLength = -1.0  ## Length of the curve (<0 means 'not measured')

  def setNumberOfIntermediatePoints(self,npts):
    if npts > 0:
      self.NumberOfIntermediatePoints = npts
    self.updateCurve()

  def setTubeRadius(self, radius):
    self.TubeRadius = radius
    self.updateCurve()

  def setInterpolationMethod(self, method):
    if method > 3 or method < 0:
      self.InterpolationMethod = 0
    else:
      self.InterpolationMethod = method
    self.updateCurve()

  def setRing(self, switch):
    self.RingMode = switch
    self.updateCurve()
    
  def enableAutomaticUpdate(self, auto):
    self.AutomaticUpdate = auto
    self.updateCurve()

  def controlPointsUpdated(self,caller,event):
    if caller.IsA('vtkMRMLMarkupsFiducialNode') and event == 'ModifiedEvent':
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
    nInterpolatedPoints = 400
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
      nOutputPoints = p+1
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

      
  def updateCurve(self):

    if self.AutomaticUpdate == False:
      return

    if self.SourceNode and self.DestinationNode:

      if self.SourceNode.GetNumberOfFiducials() < 2:
        if self.CurvePoly == None:
          self.CurvePoly.Initialize()

        self.CurveLength = 0.0

      else:

        if self.CurvePoly == None:
          self.CurvePoly = vtk.vtkPolyData()
        
        if self.DestinationNode.GetDisplayNodeID() == None:
          modelDisplayNode = slicer.vtkMRMLModelDisplayNode()
          modelDisplayNode.SetColor(self.ModelColor)
          slicer.mrmlScene.AddNode(modelDisplayNode)
          self.DestinationNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
        
        if self.InterpolationMethod == 0:
        
          if self.RingMode > 0:
            self.nodeToPoly(self.SourceNode, self.CurvePoly, True)
          else:
            self.nodeToPoly(self.SourceNode, self.CurvePoly, False)
        
        elif self.InterpolationMethod == 1: # Cardinal Spline
        
          if self.RingMode > 0:
            self.nodeToPolyCardinalSpline(self.SourceNode, self.CurvePoly, True)
          else:
            self.nodeToPolyCardinalSpline(self.SourceNode, self.CurvePoly, False)
        
        elif self.InterpolationMethod == 2: # Hermite Spline
        
          if self.RingMode > 0:        
            self.nodeToPolyHermiteSpline(self.SourceNode, self.CurvePoly, True)
          else:
            self.nodeToPolyHermiteSpline(self.SourceNode, self.CurvePoly, False)
          
        self.CurveLength = self.calculateLineLength(self.CurvePoly)

      tubeFilter = vtk.vtkTubeFilter()
      tubeFilter.SetInputData(self.CurvePoly)
      tubeFilter.SetRadius(self.TubeRadius)
      tubeFilter.SetNumberOfSides(20)
      tubeFilter.CappingOn()
      tubeFilter.Update()

      self.DestinationNode.SetAndObservePolyData(tubeFilter.GetOutput())
      self.DestinationNode.Modified()
      
      if self.DestinationNode.GetScene() == None:
        slicer.mrmlScene.AddNode(self.DestinationNode)
        
