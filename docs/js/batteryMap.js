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

    var shortSummaryLabelGroups = {
        planning: new L.FeatureGroup(),
        construction: new L.FeatureGroup(),
        operation: new L.FeatureGroup(),
        cancelled: new L.FeatureGroup(),
    }

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
            
            var label = L.marker([p.lat, p.long]);
            var div = L.divIcon({
            "className": "map-label", 
            "html": `<span class="text-nowrap bg-white">&nbsp;${p.emojis}${p.name_short}&nbsp;</span> <span class="text-nowrap bg-white">&nbsp;${p.mwh}MWh&nbsp;</span>`,
            "iconAnchor": [0, 0]});
            label.setIcon(div);
            shortSummaryLabelGroups[p["status"]].addLayer(label);
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


    // only show the operation layer for the big battery map for now
    starting_layers = [streets, overlays["operation"], overlays["cancelled"]];
    if (projects.length < 200){
        starting_layers.push(overlays["planning"]);
        starting_layers.push(overlays["construction"]);
    }
    

    var mymap = L.map(mapId, {
        // sets what is shown
        layers: starting_layers,
        // TODO: is there a way how you can set it to ctrl + wheel
        scrollWheelZoom: true,
    }).setView(zoom_coords, zoom_level);

    L.control.layers(baseLayers, overlays).addTo(mymap);

    // only show labels on certain zoom level
    mymap.on('zoomend', function() {
        console.log("zoom", mymap.getZoom());
        const overlayKeys = ["planning", "construction", "operation", "cancelled"];
        if (mymap.getZoom() < 8){
            for (const key of overlayKeys) {
                mymap.removeLayer(shortSummaryLabelGroups[key]);
            }
        } else {
            for (const key of overlayKeys) {
                if (mymap.hasLayer(overlays[key])) {
                  console.log(`Overlay layer (${key}) is added to the map`);
                  mymap.addLayer(shortSummaryLabelGroups[key]);
                }
            }  
        }

        let i = 0;
        mymap.eachLayer(function(){ i += 1; });
        console.log('Map has', i, 'layers.');
    });

    // Define callback functions
    function onOverlayAdd(e) {
        const layerName = e.name; // Name of the overlay layer that was added
        // Add your custom logic here 
        if (mymap.getZoom() >= 8) {
            console.log(`Layer added as zoom (${mymap.getZoom()}) is close: ${layerName}`);
            mymap.addLayer(shortSummaryLabelGroups[layerName])
        }
    }

    function onOverlayRemove(e) {
        const layerName = e.name; // Name of the overlay layer that was removed
        console.log(`Layer removed: ${layerName}`);
        mymap.removeLayer(shortSummaryLabelGroups[layerName])
    }

    // Listen for the overlayadd and overlayremove events
    mymap.on('overlayadd', onOverlayAdd);
    mymap.on('overlayremove', onOverlayRemove);



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