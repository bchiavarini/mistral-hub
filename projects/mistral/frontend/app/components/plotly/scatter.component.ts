import {Component, OnInit, ViewChild, ElementRef} from "@angular/core";
import {Observable} from 'rxjs/Rx';

declare var Plotly: any;

@Component({
    selector: 'app-scatter-plot',
    templateUrl: './scatter.component.html'
})
export class ScatterComponent implements OnInit {
    @ViewChild("Graph", {static: true})
    private Graph: ElementRef;

    private data;
    private receivedData;

    ngOnInit() {

        this.getPlotData().subscribe(
            res => {
                this.receivedData = res;
                // TODO formatting of the data goes here.
                this.data = this.receivedData;
            });

        // this.data = {
        //     x: [array of x coordinates],
        //     y: [array of y coordinates], //keeping the length same
        //     name: 'type string, name of the trace',
        //     type: 'scattergl', //this very important to activate WebGL
        //     mode: 'line' //other properties can be found in the docs.
        // };

        const layout = {
            autoexpand: "true",
            autosize: "true",
            width: window.innerWidth - 200, //we give initial width, so if the
                                            //graph is rendered while hidden, it
                                            //takes the right shape
            margin: {
                autoexpand: "true",
                margin: 0
            },
            offset: 0,
            type: "scattergl",
            title: name, //Title of the graph
            hovermode: "closest",
            xaxis: {
                linecolor: "black",
                linewidth: 2,
                mirror: true,
                title: "Time (s)",
                automargin: true
            },
            yaxis: {
                linecolor: "black",
                linewidth: 2,
                mirror: true,
                automargin: true,
                title: 'Any other Unit'
            }
        };
        const config = {
            responsive: true,
            scrollZoom: true
        };

        this.Graph = Plotly.newPlot(
            this.Graph.nativeElement,
            this.data,
            layout,
            config);
    }


    private getPlotData(): Observable<any> {
        return Observable.of([
            {
                x: [1, 2, 3, 4],
                y: [10, 15, 13, 17],
                mode: 'markers',
                type: 'scattergl'
            },
            {
                x: [2, 3, 4, 5],
                y: [16, 5, 11, 9],
                mode: 'lines',
                type: 'scattergl'
            },
            {
                x: [1, 2, 3, 4],
                y: [12, 9, 15, 12],
                mode: 'lines+markers',
                type: 'scattergl'
            }
        ]);
    }
}
