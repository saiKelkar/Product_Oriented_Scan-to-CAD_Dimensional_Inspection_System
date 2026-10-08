Step 0: Get the L-bracket into Python, understand what the file contains, display it, and measure it's basic geometry. 
https://www.printables.com/model/199710-simple-l-bracket/files

| Stage                       | Question we're answering                 |
| --------------------------- | ---------------------------------------- |
| 1. Understand the CAD       | What does our perfect bracket look like? |
| 2. Create defective bracket | What if manufacturing goes wrong?        |
| 3. Simulate scanner         | What would a scanner see?                |
| 4. Registration             | How do we line scan and CAD up?          |
| 5. Deviation                | Where is the manufactured part wrong?    |
| 6. Measurements             | Can we measure planes / holes / etc.?    |
| 7. Tolerances               | Is each measurement acceptable?          |
| 8. Robustness               | Can we trust the result?                 |
| 9. Real scan                | Does this work outside simulation?       |
| 10. Productize              | Can someone actually use it?             |

Step 1: Understanding the CAD model
.stl file <-- isn't really a CAD model in the engineering sense. 
It is basically a surface mode out of lots of triangles. Each little triangle is defined by three 3D coordinates: (x1, y1, z1), (x2, y2, z2), (x3, y3, z3).
This is called a triangle mesh. 

STL -> Triangle Mesh -> Represents the ideal surface
vs. 
PLY -> Point Cloud -> Represents what our scanner observed

3D scanner/depth system fundamentally measures points on surfaces. 
PLY specifically isn't synonymous with point cloud - it can store meshes too. 

CAD gives us the ideal geometry. 
The STL describes a continuous-ish surface using triangles. And we don't necessarily want to throw that information away. 
```
       "WHAT SHOULD EXIST"

             CAD
              │
              ▼
       Triangle Mesh
       bracket.stl
              │
              │
          compare
              │
              │
       Point Cloud
              ▲
              │
           Scanner

        "WHAT EXISTS"
```

Why are we about to sample the CAD into a point cloud?
We don't have a scanner yet. We only have the .stl file. But eventually our algorithm needs to work on something resembling. 
So we are going to pretend to be the scanner. Open3D will randomly sample points from the surface of the STL, and this will be our synthetic scan. 

Later, we'll make the synthetic scan increasingly horrible to challenge our algorithm - "Here's a messy cloud of points. Figure out where this object is and whether it matches the CAD."

**Mesh vs point cloud isn't "which one is better?" It's "which representation is appropriate for the operation I'm performing?"**

FPFH (Fast Point Feature Histogram) - "What does the local geometry around this point look like?"
FPFH uses relationships between neighboring points and their normals to produce a numerical description of local geometry. 

RANSAC - "Let's repeatedly try combinations of candidate matches and find a transformation supported by lots of them."
ICP (Iterative Closest Point) - repeats
1. Find corresponding nearby points
2. Estimate transformation that reduces their distances
3. Move scan
4. Repeat