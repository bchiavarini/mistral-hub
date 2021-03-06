import { Component, Input } from '@angular/core';

import { environment } from '@rapydo/../environments/environment';

@Component({
  selector: 'customlinks',
  templateUrl: './custom.navbar.links.html',
})
export class CustomNavbarComponent {

  @Input() user: any;

  constructor() { }

}


@Component({
  selector: 'custombrand',
  templateUrl: './custom.navbar.brand.html',
})
export class CustomBrandComponent {

  public myproject: string

  constructor() {
    var t = environment.projectTitle;
    t = t.replace(/^'/, "");
    t = t.replace(/'$/, "");
    this.myproject = t; 
  }

}
