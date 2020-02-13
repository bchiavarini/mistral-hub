import {Component, OnInit, Output, EventEmitter} from '@angular/core';
import {FormBuilder, FormGroup, Validators, FormControl} from '@angular/forms';
import {KeyValuePair, Fields, Runs, Areas, Resolutions, Platforms, Envs} from '../services/data';
import {MeteoFilter} from "../services/meteo.service";
import {AuthService} from '@rapydo/services/auth';

@Component({
    selector: 'app-map-filter',
    templateUrl: './map-filter.component.html',
    styleUrls: ['./map-filter.component.css']
})
export class MapFilterComponent implements OnInit {
    filterForm: FormGroup;
    fields: KeyValuePair[] = Fields;
    runs: KeyValuePair[] = Runs;
    resolutions: KeyValuePair[] = Resolutions;
    platforms: KeyValuePair[] = Platforms;
    envs: KeyValuePair[] = Envs;
    areas: KeyValuePair[] = Areas;
    user;

    @Output() onFilterChange: EventEmitter<MeteoFilter> = new EventEmitter<MeteoFilter>();

    constructor(private fb: FormBuilder, private authService: AuthService) {
        this.filterForm = this.fb.group({
            field: ['prec3', Validators.required],
            run: ['00', Validators.required],
            res: ['lm2.2', Validators.required],
            platform: [''],
            env: [''],
            area: ['Italia', Validators.required]
        });
    }

    ngOnInit() {
        this.user = this.authService.getUser();
        if (this.user.isAdmin) {
            (this.filterForm.controls.platform as FormControl).setValue('GALILEO');
            (this.filterForm.controls.env as FormControl).setValue('PROD');
        }
        // subscribe for form value changes
        this.onChanges();
        // apply filter the first time
        this.filter();
    }

    private onChanges(): void {
        this.filterForm.get('area').valueChanges.subscribe(val => {
           if (val === 'Area_Mediterranea') {
               this.filterForm.get('resolution').setValue('lm5', {emitEvent: false});
           }
        });
        this.filterForm.valueChanges.subscribe(val => {
            this.filter();
        });
    }

    private filter() {
        let filter: MeteoFilter = this.filterForm.value;
        if (filter.env === '') {delete filter['env']}
        if (filter.platform === '') {delete filter['platform']}
        this.onFilterChange.emit(filter);
    }

}
