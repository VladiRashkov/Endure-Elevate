import polyline
import folium
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import mpld3
from geopy.distance import geodesic
import os
from src.utils.helpers import format_pace


def generate_elevation_chart(elevation_high, elevation_low):
    plt.figure(figsize=(6, 3))
    elevation_gain = elevation_high - elevation_low
    labels = ["Elevation Gain"]  
    values = [elevation_gain]  

    plt.bar(labels, values, color="green")
    plt.title("Elevation Gain")
    plt.ylabel("Meters")
    plt.xticks([])
    plt.show()
    return mpld3.fig_to_html(plt.gcf())

    

def generate_heart_rate_chart(avg_hr, max_hr):
    plt.figure(figsize=(6, 3))
    heart_rates = [avg_hr, max_hr]
    labels = ["Average", "Max"]
    colors = ["blue", "red"]
    bars = plt.bar(labels, heart_rates, color=colors)

    for bar, label in zip(bars, ["AVG", "MAX"]):
        plt.text(bar.get_x() + bar.get_width() / 2,  
                 bar.get_height() - 5,               
                 label,                              
                 ha="center",                        
                 va="center",                        
                 fontsize=12,                        
                 color="white",                      
                 fontweight="bold")                  
    plt.xticks([])

    plt.title("Heart Rate Comparison")
    plt.ylabel("Heart Rate (BPM)")

    
    return mpld3.fig_to_html(plt.gcf())




def generate_vo2_max_progress(vo2_max, max_limit=100):
    plt.figure(figsize=(6, 6))
    current_percentage = vo2_max / max_limit
    remaining_percentage = 1 - current_percentage
    
    plt.pie([current_percentage, remaining_percentage], 
            colors=["purple", "lightgray"], startangle=90, counterclock=False, 
            wedgeprops=dict(width=0.3, edgecolor='white'))

   
    plt.text(0, 0, f"{vo2_max:.1f} mL/kg/min", ha='center', va='center', fontsize=14, fontweight='bold', color="purple")
    plt.title("VO2 Max Progress")
    return mpld3.fig_to_html(plt.gcf())


def create_map(polyline_data, avg_pace, avg_gain, vo2_max, avg_hr, calories, avg_cadence):
    coordinates = polyline.decode(polyline_data)
    start_point = coordinates[0]
    info_point = coordinates[100] if len(coordinates) > 100 else coordinates[-1]
    route_map = folium.Map(location=start_point, zoom_start=14)


    folium.PolyLine(locations=coordinates, color='blue', weight=5).add_to(route_map)
    folium.Marker(location=start_point, popup="Start", icon=folium.Icon(color="green")).add_to(route_map)
    folium.Marker(location=coordinates[-1], popup="End", icon=folium.Icon(color="red")).add_to(route_map)

    
    summary_html = f"""
    <div style="font-size:14px;">
        <b>Workout Summary</b><br>
        Avg Pace: {avg_pace} min/km<br>
        Elevation Gain: {avg_gain} m<br>
        VO2 Max: {vo2_max:.2f} mL/kg/min<br>
        Avg HR: {avg_hr} bpm<br>
        Calories: {calories} kcal<br>
        Avg Cadence: {avg_cadence} spm<br>
    </div>
    """
    folium.Marker(
        location=info_point,
        popup=folium.Popup(summary_html, max_width=250),
        icon=folium.Icon(icon="info-sign", color="blue"),
    ).add_to(route_map)

    
    map_dir = "static/maps"
    os.makedirs(map_dir, exist_ok=True)
    map_path = os.path.join(map_dir, "route_map.html")
    route_map.save(map_path)

    return map_path.replace('\\', '/').replace("static/", "/static/")


def calculate_pace_dynamics(polyline_data, total_distance, total_time):
    coordinates = polyline.decode(polyline_data)
    paces = []
    distance_covered = 0
    time_covered = 0
    km_distance = 1000  

    for i in range(len(coordinates) - 1):
        start, end = coordinates[i], coordinates[i + 1]
        segment_distance = geodesic(start, end).meters
        segment_time = total_time * (segment_distance / total_distance)
        distance_covered += segment_distance
        time_covered += segment_time

        if distance_covered >= km_distance:
            minutes = int(time_covered // 60)
            seconds = int(time_covered % 60)
            paces.append(f"{minutes}:{seconds:02d}")
            distance_covered -= km_distance
            time_covered = 0

    if distance_covered > 0:
        minutes = int(time_covered // 60)
        seconds = int(time_covered % 60)
        paces.append(f"{minutes}:{seconds:02d}")

    return paces

def generate_pace_chart(paces):
    kilometers = range(1, len(paces) + 1)
    paces_in_seconds = [int(p.split(':')[0]) * 60 + int(p.split(':')[1]) for p in paces]
    float_format_paces = [i/60 for i in paces_in_seconds]
    plt.figure(figsize=(8, 4))
    plt.plot(kilometers, float_format_paces, marker='o', color='red', label="Pace (min/km)")

    y_ticks = [i for i in range(1, 10)]
    y_labels = [format_pace(t) for t in y_ticks]
    plt.xticks(kilometers)
    plt.yticks(y_ticks, y_labels)

    
    plt.title("Pace Dynamics")
    plt.xlabel("Kilometer")
    plt.ylabel("Pace (min:sec/km)")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend()

    return mpld3.fig_to_html(plt.gcf())