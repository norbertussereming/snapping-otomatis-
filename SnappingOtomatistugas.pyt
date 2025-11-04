import arcpy
import os

class Toolbox(object):
    def __init__(self):
        """Define the toolbox."""
        self.label = "Toolbox Snapping Otomatis"
        self.alias = ""
        self.tools = [AutoSnap]

class AutoSnap(object):
    def __init__(self):
        """Define the tool."""
        self.label = "Snapping otomatis norbertus"
        self.description = "Menggeser titik ke garis terdekat dalam jarak maksimum tertentu"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = [
            arcpy.Parameter(
                displayName="Layer Titik Input",
                name="in_point_layer",
                datatype="GPFeatureLayer",
                parameterType="Required",
                direction="Input"),
            arcpy.Parameter(
                displayName="Layer Garis saja iyah ",
                name="in_line_layer",
                datatype="GPFeatureLayer",
                parameterType="Required",
                direction="Input"),
            arcpy.Parameter(
                displayName="Jarak Maksimum Snapping (meter)",
                name="snap_distance",
                datatype="GPLinearUnit",
                parameterType="Required",
                direction="Input"),
            arcpy.Parameter(
                displayName="Layer Output",
                name="out_layer",
                datatype="GPFeatureLayer",
                parameterType="Derived",
                direction="Output")
        ]
        params[0].filter.list = ["Point"]
        params[1].filter.list = ["Polyline"]
        params[2].value = "50 Meters"
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        point_layer = parameters[0].valueAsText
        line_layer = parameters[1].valueAsText
        snap_distance = parameters[2].valueAsText
        
        try:
            # Konversi jarak snapping ke meter
            snap_dist_value = float(snap_distance.split()[0])
            snap_dist_units = snap_distance.split()[1]
            
            if snap_dist_units.lower() != "meters":
                snap_dist_meters = arcpy.ConvertDistanceUnit(snap_dist_value, snap_dist_units, "Meters")
            else:
                snap_dist_meters = snap_dist_value
                
            arcpy.AddMessage(f"Menggunakan jarak snapping: {snap_dist_meters} meter")
            
            # Buat feature layer sementara untuk garis
            temp_line_layer = arcpy.management.MakeFeatureLayer(line_layer, "temp_line_layer")
            
            # Mulai edit session
            workspace = arcpy.Describe(point_layer).path
            edit = arcpy.da.Editor(workspace)
            edit.startEditing(False, True)
            edit.startOperation()
            
            try:
                # Hitung jumlah titik
                count = int(arcpy.GetCount_management(point_layer).getOutput(0))
                arcpy.AddMessage(f"Memproses {count} titik...")
                
                # Buat progressor
                arcpy.SetProgressor("step", "Melakukan snapping titik...", 0, count, 1)
                
                # Loop melalui setiap titik
                with arcpy.da.UpdateCursor(point_layer, ["SHAPE@XY", "OID@"]) as cursor:
                    processed = 0
                    snapped = 0
                    
                    for row in cursor:
                        point = arcpy.Point(row[0][0], row[0][1])
                        point_geom = arcpy.PointGeometry(point)
                        
                        # Cari garis terdekat dalam jarak snapping
                        near_features = arcpy.management.SelectLayerByLocation(
                            temp_line_layer, 
                            "WITHIN_A_DISTANCE", 
                            point_geom, 
                            f"{snap_dist_meters} Meters")
                        
                        # Jika ada garis dalam jarak snapping
                        if int(arcpy.GetCount_management(near_features).getOutput(0)) > 0:
                            min_distance = float('inf')
                            closest_point = None
                            
                            with arcpy.da.SearchCursor(near_features, ["SHAPE@"]) as line_cursor:
                                for line_row in line_cursor:
                                    line = line_row[0]
                                    # Dapatkan titik terdekat pada garis
                                    result = line.queryPointAndDistance(point_geom, False)
                                    nearest_point = result[0]  # PointGeometry
                                    distance = result[1]       # Distance
                                    
                                    if distance < min_distance:
                                        min_distance = distance
                                        closest_point = nearest_point
                            
                            # Update posisi titik jika ditemukan titik terdekat
                            if closest_point:
                                # Dapatkan koordinat dari PointGeometry
                                new_x = closest_point.firstPoint.X
                                new_y = closest_point.firstPoint.Y
                                row[0] = (new_x, new_y)
                                cursor.updateRow(row)
                                snapped += 1
                        
                        processed += 1
                        arcpy.SetProgressorPosition(processed)
                        if processed % 10 == 0:
                            arcpy.AddMessage(f"Diproses {processed} dari {count} titik... ({snapped} di-snap)")
                
                arcpy.AddMessage(f"Proses selesai. {snapped} dari {count} titik berhasil di-snap.")
                
            except Exception as e:
                arcpy.AddError(f"Error selama proses snapping: {str(e)}")
                edit.abortOperation()
                raise
            finally:
                edit.stopOperation()
                edit.stopEditing(True)
                arcpy.Delete_management(temp_line_layer)
            
            parameters[3].value = point_layer
            
        except Exception as e:
            arcpy.AddError(f"Error: {str(e)}")
            raise

        return
