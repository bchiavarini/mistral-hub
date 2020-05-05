import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {Observable, forkJoin, of} from 'rxjs';
import 'rxjs/add/operator/map';
import 'rxjs/add/operator/share';
import {ApiService} from '@rapydo/services/api';
import {FIELDS_SUMMARY} from "./data";

export interface ObsFilter {
    product?: string,
    network?: string
    onlyStations?: boolean
}
export interface Network {
    id: number;
    memo: string;
    desc?: string;
}
export interface Product {
    code: string;
    desc?: string;
}

export interface FieldsSummary {
    items: Items;
}

export interface Items {
    level?: any[];
    network?: any[];
    product?: any[];
    timerange?: any[];
}

@Injectable({
    providedIn: 'root'
})
export class ObsService {

    constructor(private api: ApiService) {
    }

    getFields(): Observable<FieldsSummary> {
       //return this.api.get('fields', '', {type: 'OBS'});
        return of(FIELDS_SUMMARY);
    }

    getObservations(filter: ObsFilter) {
        return this.api.get('observations', '', filter);
    }

    getStations(filter: ObsFilter) {
        let params = {
            onlyStations: true,
            q: `reftime: >=2020-05-04 00:00,<=2020-05-04 23:59;product:${filter.product}`
        }
        if (filter.network && filter.network !== '') {
            params['networks'] = filter.network;
        }
        return this.api.get('observations', '', params);
    }
}
