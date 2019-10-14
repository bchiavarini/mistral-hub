import {Component, OnInit} from '@angular/core';
import {DataService, StorageUsage} from '../../../services/data.service';
import {NotificationService} from '/rapydo/src/app/services/notification';

@Component({
    selector: 'app-storage-usage',
    templateUrl: './storage-usage.component.html'
})
export class StorageUsageComponent implements OnInit {
    usage: StorageUsage = {quota: 0, used: 0};
    barValue = 0;

    constructor(private dataService: DataService, private notify: NotificationService) {
    }

    ngOnInit() {
        this.dataService.getStorageUsage().subscribe(resp => {
            this.usage = resp.data;
            this.barValue = (this.usage.used * 100) / this.usage.quota;
        }, error => {
            this.notify.extractErrors(error, this.notify.ERROR);
        });
    }

}
