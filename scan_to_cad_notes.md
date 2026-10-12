```
from google.colab import drive

# 1. Mount the entire Google Drive (this step is always required first)
drive.mount('/content/drive')

# 2. Set up your shortcut folder and file path
BASE_DIR = '/content/drive/MyDrive/Scan-to-CAD_System'
CAD_PATH = f"{BASE_DIR}/Lbracket.stl"

print(CAD_PATH)
```

###### Loading the mesh
Open3D reads the .stl file. 
An STL file doesn't store smooth curves; instead, it represents 3D objects as a collection of flat triangles (like a low-poly 3D video game model or origami).
```
mesh = o3d.io.read_triangle_mesh(CAD_PATH)

(output)
TriangleMesh with 2128 points and 1140 triangles
```

--> This tells that the L-bracket is made up of 2128 distinct corner points stitched together by 1140 flat triangular faces. 

###### Finding the Bounding Box
Imagine you have a physical L-bracket sitting on your desk, and you want to pack it into a shipping box. You slide it into the smallest possible cardboard box that fits it completely without tilting it. That cardboard box is the Axis-Aligned Bounding Box. 
```
bbox = mesh.get_axis_aligned_bounding_box()

min_bound = bbox.get_min_bound()
max_bound = bbox.get_max_bound()
dimensions = bbox.get_extent()

print("Minimum coordinates:", min_bound)
print("Maximum coordinates:", max_bound)

print("\nBounding Box Dimensions:")
print("X:", dimensions[0])
print("Y:", dimensions[1])
print("Z:", dimensions[2])
```

Min and Max bounds - these are the coordinates of the bottom-left-back corner and the top-right-front corner of that imaginary shipping box. 

X: 15.0, Y: 49.5, Z: 49.5 <-- this gives the exact width, length, and height of the L-bracket in whichever units the CAD file was modeled in.

###### Visualization using Plotly
Under the hood, Open3D stores the mesh as a special object. To let Plotly draw it, we have to convert it to raw NumPy arrays of numbers that Plotly understands. 
```
vertices = np.asarray(mesh.vertices)
triangles = np.asarray(mesh.triangles)
```

X, Y, Z coordinates: We split the vertex array into separate columns for all X values, all Y values, and all Z values. 
i, j, k parameters: Plotly doesn't take triangles as a single list. Instead it expects three separate lists of indices. 
- i contains the first vertex index of every triangle
- j contains the second
- k contains the third
This tells Plotly's rendering engine: "Draw a flat triangle surface by connecting vertex i, vertex j, and vertex k."
```
go.Mesh3d(
	x = vertices[:, 0], y = vertices[:, 1], z = vertices[:, 2],
	i = triangles[:, 0], j = triangles[:, 1], k = triangles[:, 2],
	opacity = 0.8
)

[rows, columns]
e.g., vertices[:, 0] 
--> [: means "Grab all the rows (all 2128 vertices)"
--> , 0 specifies the exact column index you want. Since Python counts from 0, column 0 is the X-coordinate.v
```

In data visualization, plotting libraries love to stretch shapes to fill the rectangular screen space. 
Setting aspectmode to "data", forces Plotly to respect the true 1:1:1 physical scale of your CAD model. 
If we use triangles rather than indices (the i, j, k master list of vertices), it would render multiple duplicates. For example, a single corner vertex is usually shared by several different triangles. If we didn't use indices, we would have to duplicate those exact same X, Y, Z coordinates over and over again for every triangle that touches that corner. 
By keeping a single, master list of unique vertices, and using i, j, and k as pointers, we save a massive amount of memory and ensure the mesh stays tightly glued together as a continuous, solid object rather than a pile of floating, disconnected triangles. 

