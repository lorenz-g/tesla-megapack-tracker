function generateBatteryMap(projects, mapId, zoom_to_first_project=false){
    // followed this guide 
    // https://leafletjs.com/examples/quick-start/
    // https://leafletjs.com/examples/layers-control/
    var streets = L.tileLayer('https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}', {
        attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
        maxZoom: 18,
        id: 'mapbox/streets-v11',
        tileSize: 512,
        zoomOffset: -1,
        accessToken: 'pk.eyJ1IjoiYmFuZGluaWdvIiwiYSI6ImNrc3p2YjhuNzJ3eHAydXRmbW55Y2FuZHgifQ.j5Swr0wVOityl1LecXZT6g'
    });
    var satellite = L.tileLayer('https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}', {
        attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
        maxZoom: 18,
        id: 'mapbox/satellite-v9',
        tileSize: 512,
        zoomOffset: -1,
        accessToken: 'pk.eyJ1IjoiYmFuZGluaWdvIiwiYSI6ImNrc3p2YjhuNzJ3eHAydXRmbW55Y2FuZHgifQ.j5Swr0wVOityl1LecXZT6g'
    });

    var baseLayers = {
        "Streets": streets,
        "Satellite": satellite,
    };

    var overlays = {
        planning: [],
        construction: [],
        operation: [],
        cancelled: [],
    };

    var markerColor = {
        cancelled: "grey",
        planning: "grey",
        construction: "blue",
        operation: "green",
    }

    var labelGroup = new L.FeatureGroup();

    // insert the data via jinja here
    // just a hack to parse it, o/w the color highlighting in VS Code is messed up. 
    // this does not work, why?
    // var projects = '{# extra.projects_json #}';
    // projects = JSON.parse(projects)

    var p;
    var warning = "";

    for (var i=0; i < projects.length; i++){
        p = projects[i];
        if (p.coords_exact != true) {
            warning = `<br><span class="badge bg-danger">${p.coords_help_str}</span>`;
        } else {
            warning = "";
        }
        // L.Icon.Default.prototype.options, to check the default things
        var icon = L.icon({
            iconUrl:"/tesla-megapack-tracker/pics/marker-" + markerColor[p.status]+ ".png",
            iconAnchor: [12, 41],
            iconSize: [25, 41],
            popupAnchor: [ 1, -34],
            tooltipAnchor: [ 16, -28 ],
        }); 
            
        if (p.lat != ""){
            var marker;
            marker = L.marker([p.lat, p.long], {icon: icon});
            marker.bindPopup(
                `<b>${p.emojis_with_tooltips} ${p.name}</b> <br>${p.mwh}MWh
                <br> in: ${p.status} 
                <br> go live: ${p.go_live}
                <br> from: ${p.csv.manufacturer}
                <br> for: ${p.csv.customer} ${p.owner}
                <br><a href="${p.google_maps_link}" target="_blank">Google Maps</a>
                ${warning}
                <br><a href="/tesla-megapack-tracker/projects/${p.csv.id}.html" target="_blank">Details</a>`                );
            // TODO: find a way to quickly create icons of different colors
            // there is the div icon, or an external lib called AwesomeMarker
            overlays[p["status"]].push(marker)
            
            // TODO: find a way to only show the labels for the layers that a selected
            // for now they are always shown
            var label = L.marker([p.lat, p.long]);
            var div = L.divIcon({
            "className": "map-label", 
            "html": `<span class="text-nowrap bg-white">&nbsp;${p.emojis}${p.name_short}&nbsp;</span> <span class="text-nowrap bg-white">&nbsp;${p.mwh}MWh&nbsp;</span>`,
            "iconAnchor": [0, 0]});
            label.setIcon(div);
            labelGroup.addLayer(label)

            // overlays[p["status"]].push(label)

        }
    }

    // not pretty, can you add to a layer group directly? 
    overlays = {
        "planning": L.layerGroup(overlays["planning"]),
        "construction": L.layerGroup(overlays["construction"]),
        "operation": L.layerGroup(overlays["operation"]),
        "cancelled": L.layerGroup(overlays["cancelled"]),
    };

    if (zoom_to_first_project == true){
        zoom_coords = [projects[0].lat, projects[0].long];
        zoom_level = 7;
    } else {
        zoom_coords = [35.160636, 11.096191];
        zoom_level = 2;
    };

    var mymap = L.map(mapId, {
        // sets what is shown
        layers: [streets, overlays["planning"], overlays["construction"], overlays["operation"], overlays["cancelled"]],
        // TODO: is there a way how you can set it to ctrl + wheel
        scrollWheelZoom: true,
    }).setView(zoom_coords, zoom_level);

    L.control.layers(baseLayers, overlays).addTo(mymap);

    // only show labels on certain zoom level
    mymap.on('zoomend', function() {
        console.log("zoom", mymap.getZoom());
        if (mymap.getZoom() < 8){
            mymap.removeLayer(labelGroup);
        }
        else {
            mymap.addLayer(labelGroup);
        }
    });

    // useful for refining the points, disable on production
    var popup = L.popup();
    function onMapClick(e) {
        popup
        .setLatLng(e.latlng)
        .setContent(e.latlng.toString())
        .openOn(mymap);
    }
    // mymap.on('click', onMapClick);
}