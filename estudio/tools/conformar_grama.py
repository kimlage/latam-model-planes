"""Intersect the grass footprint with the ground triangulation before baking.
Both surfaces then have identical slopes; a vertical bias alone cannot fix
intersections between independently sampled, non-planar grids.
"""
from collections import defaultdict
from math import floor
import bpy, json
from pathlib import Path
from mathutils.geometry import tessellate_polygon
from mathutils import Vector


def conformar_grama():
    ground=bpy.data.objects['SDSC_AerodromeGround']
    grass=bpy.data.objects['SDSC_MownGrass']
    ground.data.calc_loop_triangles()
    triangles=[[ground.matrix_world @ ground.data.vertices[i].co for i in t.vertices] for t in ground.data.loop_triangles]
    bins=defaultdict(list)
    def cells(points):
        for x in range(floor(min(p.x for p in points)/25),floor(max(p.x for p in points)/25)+1):
            for y in range(floor(min(p.y for p in points)/25),floor(max(p.y for p in points)/25)+1):yield x,y
    for i,tri in enumerate(triangles):
        for cell in cells(tri):bins[cell].append(i)
    vertices=[];faces=[]
    def cross(a,b,p):return (b.x-a.x)*(p.y-a.y)-(b.y-a.y)*(p.x-a.x)
    data=json.loads((Path(__file__).resolve().parents[2]/'scenario_sdsc/sdsc_osm.json').read_text())
    footprints=[]
    for parcel in data['landuse']:
        if parcel.get('landuse')!='grass':continue
        ring=[Vector((x,y,0)) for x,y in parcel['polygon_xy_m']]
        if ring[0]==ring[-1]:ring.pop()
        footprints.extend([[ring[v] if isinstance(v,int) else v for v in tri] for tri in tessellate_polygon([ring])])
    for footprint in footprints:
        footprint=list(footprint)
        for idx in {i for cell in cells(footprint) for i in bins[cell]}:
            tri=triangles[idx]; sign=1 if cross(*tri)>0 else -1
            clipped=footprint
            for a,b in zip(tri,tri[1:]+tri[:1]):
                out=[]
                for p,q in zip(clipped,clipped[1:]+clipped[:1]):
                    dp=sign*cross(a,b,p);dq=sign*cross(a,b,q)
                    if dp>=-1e-7:out.append(p)
                    if (dp>0 and dq<0) or (dp<0 and dq>0):out.append(p+(q-p)*(dp/(dp-dq)))
                clipped=out
                if len(clipped)<3:break
            if len(clipped)<3:continue
            a,b,c=tri; n=(b-a).cross(c-a)
            if abs(n.z)<1e-9:continue
            pts=[Vector((p.x,p.y,a.z-(n.x*(p.x-a.x)+n.y*(p.y-a.y))/n.z+.025)) for p in clipped]
            if abs(sum(p.x*q.y-q.x*p.y for p,q in zip(pts,pts[1:]+pts[:1])))<1e-7:continue
            start=len(vertices);vertices.extend(pts);faces.append(tuple(range(start,start+len(pts))))
    mesh=bpy.data.meshes.new('SDSC_MownGrass_conformed');mesh.from_pydata(vertices,[],faces)
    for mat in grass.data.materials:mesh.materials.append(mat)
    grass.data=mesh;grass.matrix_world.identity()
    # Freeze the same ground diagonals used for the intersection.
    g=bpy.data.meshes.new('SDSC_AerodromeGround_triangles')
    g.from_pydata([v for tri in triangles for v in tri],[],[(i,i+1,i+2) for i in range(0,len(triangles)*3,3)])
    for mat in ground.data.materials:g.materials.append(mat)
    ground.data=g;ground.matrix_world.identity()
    print('GRASS_CONFORMED',len(faces),flush=True)
