import 'ion-rangeslider/js/ion.rangeSlider.min.js';

import {NgModule, CUSTOM_ELEMENTS_SCHEMA, ModuleWithProviders} from '@angular/core';
import {NgbTimeAdapter} from '@ng-bootstrap/ng-bootstrap';
import {RouterModule, Routes} from '@angular/router';
import {DatePipe} from '@angular/common';


import {SharedModule} from '@rapydo/shared.module';
import {AuthGuard} from '@rapydo/app.auth.guard';

import {IonRangeSliderModule} from "ng2-ion-range-slider";
import {NgxSpinnerModule} from "ngx-spinner";

import {HomeComponent} from '@app/custom.home'
import {DataComponent} from '@app/components/data/data.component';
import {RequestsComponent} from "@app/components/requests/requests.component";
import {SchedulesComponent} from "@app/components/schedules/schedules.component";
import {DashboardComponent} from "@app/components/dashboard/dashboard.component";
import {StorageUsageComponent} from "@app/components/dashboard/storage-usage/storage-usage.component";
import {NgbTimeStringAdapter} from '@app/adapters/timepicker-adapter';

import {DisableControlDirective} from "@app/directives/disable-control";

/* Multi-Step Wizard Components */
import {MultiStepWizardComponent} from '@app/components/multi-step-wizard/multi-step-wizard.component';
import {NavbarComponent} from '@app/components/multi-step-wizard/navbar/navbar.component';
import {StepDatasetsComponent} from '@app/components/multi-step-wizard/step-datasets/step-datasets.component'
import {StepFiltersComponent} from '@app/components/multi-step-wizard/step-filters/step-filters.component';
import {StepPostprocessComponent} from "@app/components/multi-step-wizard/step-postprocess/step-postprocess.component";
import {StepSubmitComponent} from "@app/components/multi-step-wizard/step-submit/step-submit.component";

/* Maps */
import {ForecastMapsComponent} from '@app/components/maps/forecast-maps/forecast-maps.component';
import {MapFilterComponent} from '@app/components/maps/forecast-maps/map-filter/map-filter.component';
import {MapSliderComponent} from '@app/components/maps/forecast-maps/map-slider/map-slider.component';
import {ObservationMapsComponent} from '@app/components/maps/observation-maps/observation-maps.component';

import {FormatDatePipe} from '@app/pipes/format-date.pipe';
import {WorkflowGuard} from "@app/services/workflow-guard.service";

const appRoutes: Routes = [
    {
        path: 'app/data',
        component: DataComponent, canActivate: [AuthGuard], runGuardsAndResolvers: 'always',
        children: [
            {path: '', redirectTo: 'datasets', pathMatch: 'full'},
            {path: 'datasets', component: StepDatasetsComponent},
            {path: 'filters', component: StepFiltersComponent, canActivate: [WorkflowGuard]},
            {path: 'postprocess', component: StepPostprocessComponent, canActivate: [WorkflowGuard]},
            {path: 'submit', component: StepSubmitComponent, canActivate: [WorkflowGuard]}
        ]
    },
    {path: 'app/requests', component: DashboardComponent, canActivate: [AuthGuard]},
    {path: 'app/maps/forecasts', component: ForecastMapsComponent, canActivate: [AuthGuard]},
    {path: 'app/maps/observations', component: ObservationMapsComponent, canActivate: [AuthGuard]},
    {path: 'app', redirectTo: '/app/data/datasets', pathMatch: 'full'},
    {path: '', redirectTo: '/app/data/datasets', pathMatch: 'full'},
];

@NgModule({
    imports: [
        SharedModule,
        RouterModule.forChild(appRoutes),
        IonRangeSliderModule,
        NgxSpinnerModule
    ],
    declarations: [
        HomeComponent,
        DataComponent,
        ForecastMapsComponent,
        MapFilterComponent,
        MapSliderComponent,
        ObservationMapsComponent,
        MultiStepWizardComponent,
        NavbarComponent,
        StepDatasetsComponent,
        StepFiltersComponent,
        StepPostprocessComponent,
        StepSubmitComponent,
        DashboardComponent,
        StorageUsageComponent,
        RequestsComponent,
        SchedulesComponent,
        FormatDatePipe,
        DisableControlDirective
    ],
    schemas: [CUSTOM_ELEMENTS_SCHEMA],
    providers: [
        DatePipe, {provide: NgbTimeAdapter, useClass: NgbTimeStringAdapter}],
    exports: [
        RouterModule
    ]
})

export class CustomModule {
} 
