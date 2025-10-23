import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { PhoneSwapRequestService } from '../services/phone-swap-request.service';
import { MatSnackBar } from '@angular/material/snack-bar'; // Import MatSnackBar

@Component({
  selector: 'app-phone-swap-request',
  templateUrl: './phone-swap-request.component.html',
  styleUrls: ['./phone-swap-request.component.scss']
})
export class PhoneSwapRequestComponent implements OnInit {
  swapRequestForm: FormGroup;

  constructor(
    private fb: FormBuilder,
    private swapService: PhoneSwapRequestService,
    private snackBar: MatSnackBar // Inject MatSnackBar
  ) {
    this.swapRequestForm = this.fb.group({
      currentPhone: ['', Validators.required],
      desiredPhone: ['', Validators.required],
      reason: [''],
      contactEmail: ['', [Validators.required, Validators.email]],
      contactPhone: ['', Validators.pattern('[- +()0-9]+')] // Basic phone validation
    });
  }

  ngOnInit(): void {
  }

  onSubmit(): void {
    if (this.swapRequestForm.valid) {
      this.swapService.submitRequest(this.swapRequestForm.value).subscribe({
        next: (response) => {
          console.log('Request submitted successfully', response);
          this.snackBar.open('Request submitted successfully!', 'Close', { // Use MatSnackBar
            duration: 3000,
          });
          this.swapRequestForm.reset(); // Clear the form
        },
        error: (error) => {
          console.error('Error submitting request', error);
          this.snackBar.open('Error submitting request. Please try again.', 'Close', { // Use MatSnackBar
            duration: 5000,
          });
        }
      });
    } else {
      // Display error messages or highlight invalid fields
      this.snackBar.open('Please fill in all required fields correctly.', 'Close', { // Use MatSnackBar
        duration: 5000,
      });
    }
  }

  // Getter methods for easy access to form controls
  get currentPhone() { return this.swapRequestForm.get('currentPhone'); }
  get desiredPhone() { return this.swapRequestForm.get('desiredPhone'); }
  get reason() { return this.swapRequestForm.get('reason'); }
  get contactEmail() { return this.swapRequestForm.get('contactEmail'); }
  get contactPhone() { return this.swapRequestForm.get('contactPhone'); }
}