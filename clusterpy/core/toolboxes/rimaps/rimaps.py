from mrpolygons import mrpolygon, scalePolygon, polarPolygon2cartesian, transportPolygonGeometry, transportPolygon
import Polygon
Polygon.setTolerance(1e-3)
from Polygon import Polygon
from Polygon.Utils import fillHoles, prunePoints, reducePoints
import numpy
import os
import sys
import imp
path = os.path.split(__file__)[0]
path = os.path.split(path)[0]
path = os.path.split(path)[0]
inputs = imp.load_source('inputs',path)
componentsIO = imp.load_source('componentsIO',path)


def line2pointIntersection(line,point,tol):
    if line.distance(point) < tol:
        return point
    else:
        return None

def line2mpointsIntersection(line,mpoints,tol):
    result = []
    for point in mpoints:
        if line2pointIntersection(line,point,tol) != None:
            result.append(point)
    if len(result) >= 2:
        intersection = result.sort(key=lambda x: Point(line.coords[0]).distance(Point(x)))
    return result

class rimap():
    def __init__(self,n=3600,N=30,alpha=[0.1,0.5],sigma=[1.2,1.5],dt=0.1,pg=0.1653,pu=0.4116,su=0.3997,boundary=""):
        """Creates an irregular maps

        :param n: number of areas 
        :type n: integer
        :param N: number of points sampled from each irregular polygon (MR-Polygon) 
        :type N: integer
        :param alpha: min and max value to sampled alpha; default is (0.1,0.5)
        :type alpha: List
        :param sigma: min and max value to sampled sigma; default is (1.2,1.5)
        :type sigma: List
        :param dt: time delta to be used to create irregular polygons (MR-Polygons)
        :type dt: Float
        :param pg: parameter to define the scaling factor of each polygon before being introduced as part of the irregular map
        :type pg: Float
        :param pu: parameter to define the probability of increase the number of areas of each polygon before being introduced into the irregular map
        :type pu: Float
        :param su: parameter to define how much is increased the number of areas of each polygon before being introduced into the irregular map
        :type su: Float
        :param boundary: Initial irregular boundary to be used into the recursive irregular map algorithm
        :type boundary: Layer

        :rtype: Layer
        :return: RI-Map instance 
        """
        self.carteAreas = []
        self.carteExternal = []
        self.n = n
        self.pg = pg
        self.pu = pu
        self.su = su
        # Initializing area parameters
        self.alpha = alpha
        self.sigma = sigma
        self.N = N + 1
        self.mu = 10
        self.X_0 = 10
        self.dt = dt
        alp = 0.4
        sig = 1.2
        self.lAreas = 0
        print dt
        if boundary == "":
            a,r,sa,sr,X1,times = mrpolygon(alp,sig,self.mu,self.X_0,self.dt,self.N)
            sa,sr = scalePolygon(sa,sr,1000)
            polygon = polarPolygon2cartesian(zip(sa,sr))
        else:
            layer = inputs.importArcData(boundary)
            polygon = layer.areas[0][0]
        polygon = Polygon(polygon)
        self.areasPerLevel = {}
        self.oPolygon = polygon
        areas, coveredArea = self.dividePolygon(polygon,Polygon(),self.n,0.97)
        areaUnion = Polygon()
        if len(areas) > n:
            areas = self.postCorrectionDissolve(areas,n)
        for a in areas:
            a = a[0]
            if a[-1] != a[0]:
                a.append(a[0])
            self.carteAreas.append([a])
        print "closing: " + str(len(self.carteAreas))

    def postCorrectionDissolve(self,areas,nAreas,areaUnion):
        def deleteAreaFromW(areaId,newId,W):
            neighs = W[areaId]
            W.pop(areaId)
            for n in neighs:
                W[n].remove(areaId)
                if n != newId:
                    W[n].append(newId)
                    W[n] = list(set(W[n]))
            W[newId].extend(neighs)
            W[newId] = list(set(W[newId]))
            W[newId].remove(newId)
            return W
        pos = 0
        Wrook, Wqueen = componentsIO.WfromPolig(areas)
        aIds = filter(lambda x: len(Wrook[x])>0,Wrook.keys())
        aIds0 = filter(lambda x: len(Wrook[x])==0,Wrook.keys())
        areas = [areas[x] for x in aIds]
        areas.sort(key = lambda x: len(x[0]))
        Wrook, Wqueen = componentsIO.WfromPolig(areas)
        availableAreas = Wrook.keys()
        end = False
        pos = availableAreas.pop(0)
        id2pos = Wrook.keys()
        while len(areas) > nAreas and not end:
            area = areas[id2pos.index(pos)]
            if len(Wrook[pos]) > 0:
                neighs = Wrook[pos]
                neighs.sort(key=lambda x: areas[id2pos.index(x)].area())
                neighs.reverse()
                for k,nneigh in enumerate(neighs):
                    neigh = areas[id2pos.index(nneigh)]
                    narea = area | neigh
                    if len(narea) == 1:
                        areas[id2pos.index(nneigh)] = narea
                        Wrook = deleteAreaFromW(pos,nneigh,Wrook)
                        areas.pop(id2pos.index(pos))
                        id2pos.remove(pos)
                        try:
                            availableAreas.remove(pos)
                        except:
                            pass
                        break
                if len(areas) == nAreas:
                    end = True
                    break
                else:
                    if len(availableAreas) > 0:
                        pos = availableAreas.pop(0)
                    else:
                        end = True
            else:
                Wrook.pop(pos)
                area = areas.pop(id2pos.index(pos))
                id2pos.remove(pos)
                try:
                    availableAreas.remove(pos)
                except:
                    pass
                if len(availableAreas) > 0:
                    pos = availableAreas.pop(0)
                else:
                    end = True

        return areas,areaUnion

    def postCorrectionHoles(self,polygon,areas):
        exterior = fillHoles(polygon)
        holes = exterior - polygon
        "5. Agregando huecos"
        for hole in holes:
            areas.append(Polygon(hole))
        return areas

    def postDividePolygons(self,areas,nAreas):
        def getPointInFace(face,bbox):
            if face == 0:
                x = bbox[0]
                y = numpy.random.uniform(bbox[2],bbox[3])
            elif face == 1:
                y = bbox[3]
                x = numpy.random.uniform(bbox[0],bbox[1])
            elif face == 2:
                x = bbox[1]
                y = numpy.random.uniform(bbox[2],bbox[3])
            elif face == 3:
                y = bbox[2]
                x = numpy.random.uniform(bbox[0],bbox[1])
            return x,y

        def getCornersOfFace(face,bbox):
            if face == 0:
                c1 = (bbox[0],bbox[2])
                c2 = (bbox[0],bbox[3])
            elif face == 1:
                c1 = (bbox[0],bbox[3])
                c2 = (bbox[1],bbox[3])
            elif face == 2:
                c1 = (bbox[1],bbox[3])
                c2 = (bbox[1],bbox[2])
            elif face == 3:
                c1 = (bbox[1],bbox[2])
                c2 = (bbox[0],bbox[2])
            return c1,c2

        while len(areas) < nAreas:
            end = False
            while not end:
                areaOrder = range(0,len(areas))
                areaOrder.sort(key=lambda x: areas[x].area(),reverse=True)
                na = areaOrder[0]
                #na = numpy.random.randint(0,len(areas))
                area = areas[na]
                bbox = area.boundingBox()
                f1 = numpy.random.randint(0,4)
                f2 = (f1 + numpy.random.randint(0,3))%4
                faces = [f1,f2]
                faces.sort()
                p1 = getPointInFace(faces[0],bbox)
                p2 = getPointInFace(faces[1],bbox)
                divPolygon = [p1]
                for i in range(f1,f2):
                    c1,c2 = getCornersOfFace(i,bbox)
                    divPolygon.append(c2)
                divPolygon.append(p2)
                divPolygon.append(p1)
                divPolygon = Polygon(divPolygon)
                polygon1 = divPolygon & area
                if len(polygon1) > 1:
                    pl = [Polygon(x) for x in polygon1]
                    pl.sort(key=lambda x: x.area())
                    polygon1 = pl[-1]
                polygon2 = area - polygon1
                if len(polygon2) > 1:
                    pl = [Polygon(x) for x in polygon2]
                    pl.sort(key=lambda x: x.area())
                    polygon2 = pl[-1]

                if polygon1.area() > 0 and polygon2.area() > 0 and polygon1.area() + polygon2.area() == area.area():
                    end = True
            areas.pop(na)
            areas.append(polygon1)
            areas.append(polygon2)
        return areas

    def dividePolygon(self,polygon,coveredArea,k,fill,rec=1):
        """
            k = numero de polygonos
            fill = cantidad minima a cubrir
        """
        if k == 1:
            areas = [polygon]
            areaUnion = polygon
            self.lAreas += 1
        elif k == 2:
            areas = self.postDividePolygons([polygon],2)
            areaUnion = polygon
            self.lAreas += 2
        else:
            if k*self.pg >= 1:
                area = polygon.area()*self.pg
            else:
                area = polygon.area()*(1/float(k))
            ratio = (area/float(numpy.pi))**0.5
            scale = ratio/self.mu
            areas = []
            uncoveredArea = polygon - coveredArea
            fillOld = 0
            count = 0
            oldCovered = -1
            areaUnion = Polygon()
            newk = k
            while uncoveredArea.area()/polygon.area() >= (1-fill): # Mientras se llena al p1%
                count += 1
                if oldCovered != coveredArea.area():
                    count = 0
                if len(uncoveredArea) > 1:
                    uncovered2select = [Polygon(x) for x in uncoveredArea]
                    uncovered2select.sort(key=lambda x: x.area(),reverse=True)
                    uncovered2select = uncovered2select[0]
                else:
                    uncovered2select = uncoveredArea
                oldCovered = coveredArea.area()
                if count >= 20:
                    count += 1
                    end = False
                    while end != True:
                        uncovered2select2 = self.postDividePolygons([uncovered2select],2)
                        for x in uncovered2select2:
                            if newk*x.area()/uncoveredArea.area() <= 1.5:
                                areas.append(x)
                                uncoveredArea = uncoveredArea - x
                                coveredArea = coveredArea | x
                                areaUnion = areaUnion | x
                                end = True
                if uncoveredArea.area() > 0:
                    if newk*uncovered2select.area()/uncoveredArea.area() <= 1.5:
                        areas.append(uncovered2select)
                        uncoveredArea = uncoveredArea - uncovered2select
                        coveredArea = coveredArea | uncovered2select
                        areaUnion = areaUnion | uncovered2select
                    else:
                        center = uncoveredArea.sample(numpy.random.uniform)
                        angle = numpy.random.uniform(0,2)*numpy.pi
                        x = ratio*numpy.cos(angle) + center[0]
                        y = ratio*numpy.sin(angle) + center[1]
                        aPoint = (x,y)
                        alp = numpy.random.uniform(self.alpha[0],self.alpha[1])
                        sig = numpy.random.uniform(self.sigma[0],self.sigma[1])
                        a,r,sa,sr,X1,times = mrpolygon(alp,sig,self.mu,self.X_0,self.dt,self.N)
                        sa,sr = scalePolygon(sa,sr,scale)
                        polygoni = polarPolygon2cartesian(zip(sa,sr))
                        polygoni = transportPolygon(polygoni, center, aPoint)
                        polygoni = Polygon(polygoni)
                        polygoni = polygoni - coveredArea
                        polygoni = polygoni & polygon
                        if len(polygoni) > 1:
                            pl = [Polygon(x) for x in polygoni]
                            pl.sort(key=lambda x: x.area())
                            polygoni = pl[-1]
                        newN = numpy.round(newk*polygoni.area()/uncoveredArea.area())
                        rnd = numpy.random.uniform(0,1)
                        if rnd <= self.pu:
                            newN += numpy.round(numpy.random.uniform(0,self.su)*newk)
                        if  newN >= 1:
                            areasi, coveredAreai = self.dividePolygon(polygoni,coveredArea,newN,fill,rec=rec+1)
                            newk -= newN
                            coveredArea = coveredArea | coveredAreai
                            areaUnion = areaUnion | coveredAreai
                            areas += areasi
                            uncoveredArea = polygon - coveredArea
        areas = self.postCorrectionHoles(areaUnion,areas)
        la = len(areas)
        nAreas = []
        for nx, x in enumerate(areas):
            add = True
            for nx2, x2 in enumerate(areas):
                if x2.covers(x) and nx != nx2:
                    add = False
                    break
            if add:
                nAreas.append(x)
        l1 = len(areas)
        areas = nAreas
        l2 = len(areas)
        if len(areas) < k:
            areas = self.postDividePolygons(areas,k)
        if len(areas) > k:
            areas, areaUnion = self.postCorrectionDissolve(areas,k,areaUnion)
        coveredArea = fillHoles(areaUnion)
        l3 = len(areas)
        print self.lAreas
        return areas, coveredArea
