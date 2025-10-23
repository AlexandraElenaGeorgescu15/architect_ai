import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class PhoneSwapRequestService {

  private apiUrl = '/api/PhoneSwapRequest/request';  // Adjust the API endpoint accordingly

  constructor(private http: HttpClient) { }

  submitRequest(requestData: any): Observable<any> {
    return this.http.post(this.apiUrl, requestData);
  }
}