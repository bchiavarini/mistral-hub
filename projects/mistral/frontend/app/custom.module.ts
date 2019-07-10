import {NgModule, ModuleWithProviders} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {DatePipe} from '@angular/common';

import {RapydoModule} from '/rapydo/src/app/rapydo.module';
import {AuthGuard} from '/rapydo/src/app/app.auth.guard';

import {DataComponent} from './components/data/data.component';
import {RequestsComponent} from "./components/requests/requests.component";

/* Multi-Step Wizard Components */
import {MultiStepWizardComponent} from './components/multi-step-wizard/multi-step-wizard.component';
import {NavbarComponent} from './components/multi-step-wizard/navbar/navbar.component';
import {StepDatasetsComponent} from './components/multi-step-wizard/step-datasets/step-datasets.component'
import {StepFiltersComponent} from './components/multi-step-wizard/step-filters/step-filters.component';
import {StepPostprocessComponent} from "./components/multi-step-wizard/step-postprocess/step-postprocess.component";
import {StepSubmitComponent} from "./components/multi-step-wizard/step-submit/step-submit.component";

/* Shared Service */
import {FormDataService} from './services/formData.service';
import {WorkflowService} from './services/workflow.service';
import {DataService} from "./services/data.service";
import {FormatDatePipe} from "./components/pipes/format-date.pipe";


const routes: Routes = [
    {
        path: 'app/data',
        component: DataComponent, canActivate: [AuthGuard], runGuardsAndResolvers: 'always',
        children: [
            {path: '', redirectTo: '/app/data/(step:datasets)', pathMatch: 'full'},
            {path: 'datasets', component: StepDatasetsComponent, outlet: 'step'},
            {path: 'filters', component: StepFiltersComponent, outlet: 'step'},
            {path: 'postprocess', component: StepPostprocessComponent, outlet: 'step'},
            {path: 'submit', component: StepSubmitComponent, outlet: 'step'}
        ]
    },

    {path: 'app/requests', component: RequestsComponent},
    {path: 'app', redirectTo: '/app/data', pathMatch: 'full'},
    {path: '', redirectTo: '/app/data', pathMatch: 'full'},
];

@NgModule({
    imports: [
        RapydoModule,
        RouterModule.forChild(routes)
    ],
    declarations: [
        DataComponent,
        MultiStepWizardComponent,
        NavbarComponent,
        StepDatasetsComponent,
        StepFiltersComponent,
        StepPostprocessComponent,
        StepSubmitComponent,
        RequestsComponent,
        FormatDatePipe
    ],
    providers: [FormDataService, WorkflowService, DataService, DatePipe],
    exports: [
        RouterModule
    ]
})

export class CustomModule {
} 
