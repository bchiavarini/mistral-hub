import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup, FormArray, FormControl, Validators} from '@angular/forms';
import {FormDataService} from "../../../services/formData.service";
import {NotificationService} from '/rapydo/src/app/services/notification';
import {ArkimetService} from "../../../services/arkimet.service";
import {Filters} from "../../../services/data.service";
import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import * as moment from 'moment';

@Component({
    selector: 'step-filters',
    templateUrl: './step-filters.component.html'
})
export class StepFiltersComponent implements OnInit {
    title = 'Filter your data';
    loading: boolean = false;
    summaryStats = {};
    filterForm: FormGroup;
    filters: Filters;
    disabledDp = false;

    constructor(private fb: FormBuilder,
                private router: Router,
                private route: ActivatedRoute,
                private formDataService: FormDataService,
                private arkimetService: ArkimetService,
                private modalService: NgbModal,
                private notify: NotificationService) {
        const refTime = this.formDataService.getReftime();
        this.filterForm = this.fb.group({
            filters: this.fb.array([]),
            fromDate: new FormControl({value: refTime ? refTime.from : this.formDataService.getDefaultRefTime().from, disabled: true}),
            fromTime: new FormControl({value: refTime ? moment(refTime.from).format('HH:mm') : '00:00', disabled: true}),
            toDate: new FormControl({value: refTime ? refTime.to : this.formDataService.getDefaultRefTime().to, disabled: true}),
            toTime: new FormControl({value: refTime ? moment(refTime.to).format('HH:mm') : '00:00', disabled: true}),
            fullDataset: [false],
            validRefTime: [false, Validators.requiredTrue]
        });
    }

    ngOnInit() {
        this.loadFilters();
        window.scroll(0, 0);
    }

    today() {
        const today = moment();
        return {year: today.year(), month: today.month()+1, day: today.date()};
    }

    private addFilter(name: string, values: any): FormGroup {
        let filter = this.fb.group({
            name: [name, Validators.required],
            values: new FormArray([])
        });
        // init values
        values.map(o => {
            // pre-set actual values from formData
            const control = new FormControl(this.formDataService.isFilterSelected(o));
            (filter.controls.values as FormArray).push(control);
        });
        return filter;
    }

    private loadFilters() {
        console.log('current filters', this.filters);
        this.loading = true;
        // reset filters
        (this.filterForm.controls.filters as FormArray).clear();
        this.formDataService.getFilters().subscribe(
            response => {
                this.filters = response.data.items;
                this.summaryStats = response.data.items.summarystats;
                if (!this.summaryStats.hasOwnProperty('b')) {
                    let from = moment(this.formDataService.getReftime().from);
                    this.summaryStats['b'] = [from.year(), from.month()+1, from.date(), from.hour(), from.minute(), from.second()]
                }
                if (!this.summaryStats.hasOwnProperty('e')) {
                    let to = moment(this.formDataService.getReftime().to);
                    this.summaryStats['e'] = [to.year(), to.month()+1, to.date(), to.hour(), to.minute(), to.second()]
                }
                Object.entries(response.data.items).forEach(entry => {
                    if (entry[0] !== 'summarystats') {
                        (this.filterForm.controls.filters as FormArray).push(this.addFilter(entry[0], entry[1]));
                    }
                });
                //console.log(this.filterForm.get('filters'));
                //console.log(this.filters);
                if (this.summaryStats['s'] === 0) {
                    (this.filterForm.controls.validRefTime as FormControl).setValue(false);
                    this.notify.showWarning('The applied reference time does not produce any result. ' +
                        'Please choose a different reference time range.');
                } else {
                    (this.filterForm.controls.validRefTime as FormControl).setValue(true);
                }
            },
            error => {
                this.notify.showError(`Unable to get summary fields`);
            }
        ).add(() => {
            this.loading = false;
        });
    }

    toggleFullDataset() {
        this.disabledDp = !this.disabledDp;
        (this.filterForm.controls.fullDataset as FormControl).setValue(this.disabledDp);
        this.checkRefTimeControls();
    }

    private checkRefTimeControls() {
        if (this.disabledDp) {
            (this.filterForm.controls.fromDate as FormControl).disable();
            (this.filterForm.controls.fromTime as FormControl).disable();
            (this.filterForm.controls.toDate as FormControl).disable();
            (this.filterForm.controls.toTime as FormControl).disable();
        } else {
            (this.filterForm.controls.fromDate as FormControl).enable();
            (this.filterForm.controls.fromTime as FormControl).enable();
            (this.filterForm.controls.toDate as FormControl).enable();
            (this.filterForm.controls.toTime as FormControl).enable();
        }
    }

    editReftime(content) {
        const modalRef = this.modalService.open(content);
        let fullDataset = !this.formDataService.getReftime();
        setTimeout(() => {
          this.disabledDp = fullDataset;
          this.filterForm.get('fullDataset').setValue(fullDataset ? true : false);
          this.checkRefTimeControls();
        });
        modalRef.result.then((result) => {
            if (this.filterForm.controls.fullDataset.value) {
                this.formDataService.setReftime(null);
            } else {
                let fromDate: Date = this.filterForm.get('fromDate').value;
                const fromTime = this.filterForm.get('fromTime').value.split(':');
                fromDate.setHours(parseInt(fromTime[0]), parseInt(fromTime[1]));
                let toDate: Date = this.filterForm.get('toDate').value;
                const toTime = this.filterForm.get('toTime').value.split(':');
                toDate.setHours(parseInt(toTime[0]), parseInt(toTime[1]));
                this.formDataService.setReftime({
                    from: fromDate,
                    to: toDate
                });
            }
            this.loadFilters();
        }, (reason) => {
            // do nothing
        });
    }

    private save() {
        if (!this.filterForm.valid) {
            return false;
        }
        const selectedFilters = [];
        this.filterForm.value.filters.forEach(f => {
            let res = {
                name: f.name,
                values: f.values
                    .map((v, j) => v ? this.filters[f.name][j] : null)
                    .filter(v => v !== null),
                query: ''
            };
            if (res.values.length) {
                res.query = this.arkimetService.getQuery(res);
                selectedFilters.push(res);
            }
        });
        // console.log(`selected filters: ${selectedFilters}`);
        this.formDataService.setFilters(selectedFilters);
        return true;
    }

    goToPrevious() {
        if (this.save()) {
            // Navigate to the dataset page
            this.router.navigate(
                ['../', 'datasets'], {relativeTo: this.route});
        }
    }

    goToNext(form: any) {
        if (this.save()) {
            // Navigate to the postprocess page
            this.router.navigate(
                ['../', 'postprocess'], {relativeTo: this.route});
        }
    }
}
