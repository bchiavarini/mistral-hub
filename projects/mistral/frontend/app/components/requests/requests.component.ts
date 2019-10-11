import {Component, ChangeDetectorRef} from '@angular/core';
import {saveAs as importedSaveAs} from "file-saver";
import {BasePaginationComponent} from '@rapydo/components/base.pagination.component';

import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import {ApiService} from '@rapydo/services/api';
import {AuthService} from '@rapydo/services/auth';
import {NotificationService} from '@rapydo/services/notification';
import {FormlyService} from '@rapydo/services/formly'
import {DataService} from "@app/services/data.service";

@Component({
    selector: 'app-requests',
    templateUrl: './requests.component.html',
    styleUrls: ['./requests.component.css']
})
export class RequestsComponent extends BasePaginationComponent {
    expanded: any = {};

    constructor(
        protected api: ApiService,
        protected auth: AuthService,
        protected notify: NotificationService,
        protected modalService: NgbModal,
        protected formly: FormlyService,
        protected changeDetectorRef: ChangeDetectorRef,
        private dataService: DataService,
    ) {
        super(api, auth, notify, modalService, formly, changeDetectorRef);
        this.init("request");

        this.server_side_pagination = true;
        this.endpoint = 'requests';
        this.counter_endpoint = 'requests';
        this.initPaging(20);
        this.list();
    }

    list() {
        return this.get(this.endpoint);
    }

    remove(requestID) {
        console.log(`remove this request ${requestID}`);
        return this.delete('requests', requestID);
    }

    download(filename) {
        this.dataService.downloadData(filename).subscribe(
            resp => {
                const contentType = resp.headers['content-type'] || 'application/octet-stream';
                const blob = new Blob([resp.body], {type: contentType});
                importedSaveAs(blob, filename);
            },
            error => {
                this.notify.showError(`Unable to download file: ${filename}`);
            }
        );
    }

    toggleExpandRow(row) {
        this.table.rowDetail.toggleExpandRow(row);
    }
}
