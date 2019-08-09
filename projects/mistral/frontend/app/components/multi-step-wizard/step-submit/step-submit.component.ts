import {Component, OnInit, Input} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormDataService} from "../../../services/formData.service";
import {FormData} from "../../../services/formData.model";
import {DataService, SummaryStats} from "../../../services/data.service";
import {NotificationService} from '/rapydo/src/app/services/notification';

@Component({
    selector: 'step-submit',
    templateUrl: './step-submit.component.html'
})
export class StepSubmitComponent implements OnInit {
    title = 'Submit your request';
    summaryStats: SummaryStats = {c:0, s: 0};
    @Input() formData: FormData;
    isFormValid: boolean = false;

    constructor(
        private router: Router,
        private route: ActivatedRoute,
        private dataService: DataService,
        private formDataService: FormDataService,
        private notify: NotificationService
    ) {
    }

    ngOnInit() {
        this.formData = this.formDataService.getFormData();
        this.isFormValid = this.formDataService.isFormValid();
        this.formDataService.getSummaryStats().subscribe(r => {
            this.summaryStats = r.data;
            if (this.summaryStats.s === 0) {
                this.notify.showWarning('The applied filter do not produce any result. ' +
                        'Please choose different filters.');
            }
        });
        window.scroll(0,0);
    }

    goToPrevious() {
        // Navigate to the postprocess page
        this.router.navigate(
            ['../', 'postprocess'], {relativeTo: this.route});
    }

    submit(form: any) {
        console.log('submit request for data extraction');
        this.dataService.extractData(this.formData).subscribe(
            resp => {
                this.formData = this.formDataService.resetFormData();
                this.isFormValid = false;
                // Navigate to the 'My Requests' page
                this.router.navigate(['app/requests']);
            },
            error => {
                // TODO
            }
        )
    }

}

