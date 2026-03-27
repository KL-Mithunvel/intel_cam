# Project Overview

## Title

**3D Object Reconstruction Using Intel RealSense RGB-D Camera with Background and Hand Removal**

---

## 1. Introduction

Three-dimensional reconstruction is a fundamental problem in computer vision and robotics — the goal is to recover the geometric structure of real-world objects in a digital format. With the advancement of depth-sensing technologies such as RGB-D cameras, it is now possible to reconstruct 3D models using affordable hardware.

An RGB-D camera, such as the Intel RealSense series, provides both:

- **Color information** (RGB)
- **Depth information** (distance from camera, in millimetres)

By combining multiple depth frames from different viewpoints, a complete 3D representation of an object can be reconstructed.

This project focuses on building a complete software pipeline for 3D reconstruction using:

- A stationary camera
- A manually rotated object
- A Python-based processing system

---

## 2. Motivation

### 2.1 Cost Reduction

Traditional 3D scanners are expensive and require specialised hardware. This project uses:

- A consumer-grade RGB-D camera (Intel RealSense)
- Open-source software (pyrealsense2, Open3D, OpenCV)

### 2.2 Accessibility

- Allows students and engineers to build their own 3D scanner
- Enables rapid prototyping with minimal investment

### 2.3 Applications

| Domain | Use Case |
|--------|----------|
| Robotics | Object modelling and manipulation |
| Digital twins | Virtual replicas of physical objects |
| Reverse engineering | Measuring and reproducing existing parts |
| AR/VR | Content creation from real-world objects |
| Manufacturing | Inspection and quality control |

### 2.4 Technical Challenge

A major challenge addressed by this project is **removing the operator's hand** from the depth data during scanning, so the reconstructed mesh contains only the target object.

---

## 3. Problem Statement

Design and implement a system that:

1. Captures RGB-D data from a stationary Intel RealSense camera
2. Processes the data to remove background and hand interference
3. Converts depth data into 3D point clouds
4. Aligns multiple point clouds across frames
5. Generates a smooth and complete 3D mesh
6. Exports the mesh for use in CAD and simulation tools

---

## 4. Objectives

### 4.1 Primary Objectives

- Develop a complete 3D reconstruction pipeline (capture → process → mesh)
- Generate accurate 3D meshes from RGB-D frames

### 4.2 Secondary Objectives

- Ensure clean segmentation — no hand or background artefacts in the final mesh
- Maintain a modular code architecture (each stage is an independent script)
- Enable export in formats compatible with CAD and simulation tools (e.g. `.ply`, `.obj`)

---

## 5. Scope

### Included

- RGB-D capture (`.bag` recording)
- Background capture and depth modelling
- Per-frame depth and colour export
- Point cloud generation from depth + intrinsics
- Point cloud registration (ICP)
- Mesh reconstruction (TSDF fusion)
- Mesh export

### Not Included

- Real-time reconstruction (offline pipeline only)
- Texture mapping (optional future work)
- AI-based segmentation (future scope)
- Turntable or motorised rig (object is rotated by hand)

---

## 6. Assumptions

- Camera remains fixed throughout a scan session
- Object is moved/rotated manually between frames
- Background remains static (no moving elements other than the object and hand)
- Lighting conditions are stable
- The background depth reference is captured before each session with an empty scene

---

## 7. Expected Outcomes

- Accurate 3D mesh of the scanned object
- A reusable, modular Python pipeline
- Clean segmentation — object isolated from background and hand
- Exportable mesh files ready for CAD or simulation use