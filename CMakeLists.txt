cmake_minimum_required(VERSION 2.8.9)

project(CurveMaker)

#-----------------------------------------------------------------------------
set(EXTENSION_HOMEPAGE "https://www.slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/CurveMaker")
set(EXTENSION_CATEGORY "Informatics")
set(EXTENSION_CONTRIBUTORS "Junichi Tokuda (BWH)")
set(EXTENSION_DESCRIPTION "This is a module to generate a curve based on a list of fiducial points.")
set(EXTENSION_ICONURL "https://www.slicer.org/slicerWiki/images/b/b7/CurveMakerIcon.png")
set(EXTENSION_SCREENSHOTURLS "https://www.slicer.org/slicerWiki/images/0/0b/Slicer4-CurveMaker-GUI.png")

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
add_subdirectory(CurveMaker)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
