import {Injectable} from '@angular/core';
import {ApiService} from '/rapydo/src/app/services/api';

@Injectable()
export class DataService {

    constructor(private api: ApiService) { }

    /**
     * Get all the available datasets.
     */
    getDatsets() {
        return this.api.get('datasets');
    }

    /**
     * Get summary fields for a give list of datasets.
     * @param datasets
     */
    getSummary(datasets: string[]) {
        return this.api.get('fields', '', {datasets: datasets.join()});
    }

    /**
     * Request for data extraction.
     */
    extractData() {
        let body = {
            datasets: ["vlm5"],
            filters: {
                reftime: "2019-06-03",
                origin: "GRIB1,080",
                level: "GRIB1,1"
            }
        }
        return this.api.post('data', body, { "rawResponse": true });
    }

}
