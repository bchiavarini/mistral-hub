import {Component, OnInit, ViewChild, ElementRef} from "@angular/core";
import {Observable} from 'rxjs/Rx';

declare var Plotly: any;

@Component({
    selector: 'app-map',
    templateUrl: './map.component.html'
})
export class MapComponent implements OnInit {
    @ViewChild("Graph", {static: true})
    private Graph: ElementRef;

    ngOnInit() {
        Plotly.d3.csv(
            // "https://raw.githubusercontent.com/plotly/datasets/master/2015_06_30_precipitation.csv",
            "/app/custom/assets/data/newprec3.csv",
            function (err, rows) {
                function unpack(rows, key) {
                    return rows.map(function (row) {
                        return row[key];
                    });
                }

                const data = [
                    {
                        type: "scattermapbox",
                        text: unpack(rows, "Globvalue"),
                        lon: unpack(rows, "Lon"),
                        lat: unpack(rows, "Lat"),
                        marker: {color: "fuchsia", size: 4}
                    }
                ];

                const layout = {
                    dragmode: "zoom",
                    mapbox: {style: "open-street-map", center: {lat: 44, lon: 15}, zoom: 3},
                    margin: {r: 0, t: 0, b: 0, l: 0}
                };
                console.log(data);

                Plotly.newPlot("Graph", data, layout);
            }
        );
    }


    private getObservedData(): Observable<any> {
        return Observable.of([]);
    }
}
