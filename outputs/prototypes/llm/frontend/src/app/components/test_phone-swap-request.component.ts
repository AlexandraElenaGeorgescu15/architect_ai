import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { PhoneSwapRequestComponent } from './phone-swap-request.component';
import { PhoneSwapRequestService } from '../services/phone-swap-request.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

describe('PhoneSwapRequestComponent', () => {
  let component: PhoneSwapRequestComponent;
  let fixture: ComponentFixture<PhoneSwapRequestComponent>;
  let swapService: PhoneSwapRequestService;
  let snackBar: MatSnackBar;
  let fb: FormBuilder;

  const mockSwapService = {
    submitRequest: jest.fn()
  };

  const mockSnackBar = {
    open: jest.fn()
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [PhoneSwapRequestComponent],
      imports: [
        ReactiveFormsModule,
        BrowserAnimationsModule,
        MatFormFieldModule,
        MatInputModule
      ],
      providers: [
        FormBuilder,
        { provide: PhoneSwapRequestService, useValue: mockSwapService },
        { provide: MatSnackBar, useValue: mockSnackBar }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PhoneSwapRequestComponent);
    component = fixture.componentInstance;
    swapService = TestBed.inject(PhoneSwapRequestService);
    snackBar = TestBed.inject(MatSnackBar);
    fb = TestBed.inject(FormBuilder);

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize the swapRequestForm with correct validators', () => {
    expect(component.swapRequestForm).toBeInstanceOf(FormGroup);
    expect(component.swapRequestForm.get('currentPhone')?.hasValidator(Validators.required)).toBeTruthy();
    expect(component.swapRequestForm.get('desiredPhone')?.hasValidator(Validators.required)).toBeTruthy();
    expect(component.swapRequestForm.get('contactEmail')?.hasValidator(Validators.required)).toBeTruthy();
    expect(component.swapRequestForm.get('contactEmail')?.hasValidator(Validators.email)).toBeTruthy();
    expect(component.swapRequestForm.get('contactPhone')?.hasValidator(Validators.pattern('[- +()0-9]+'))).toBeTruthy();
  });

  describe('onSubmit', () => {
    it('should call submitRequest service and open success snackbar on valid form submission', () => {
      const mockFormValue = {
        currentPhone: '123-456-7890',
        desiredPhone: '098-765-4321',
        reason: 'Upgrade',
        contactEmail: 'test@example.com',
        contactPhone: '111-222-3333'
      };
      component.swapRequestForm.setValue(mockFormValue);
      (mockSwapService.submitRequest as jest.Mock).mockReturnValue(of({}));

      component.onSubmit();

      expect(mockSwapService.submitRequest).toHaveBeenCalledWith(mockFormValue);
      expect(snackBar.open).toHaveBeenCalledWith('Request submitted successfully!', 'Close', { duration: 3000 });
      expect(component.swapRequestForm.value.currentPhone).toEqual('123-456-7890');
      expect(component.swapRequestForm.value.desiredPhone).toEqual('098-765-4321');
      expect(component.swapRequestForm.value.reason).toEqual('Upgrade');
      expect(component.swapRequestForm.value.contactEmail).toEqual('test@example.com');
      expect(component.swapRequestForm.value.contactPhone).toEqual('111-222-3333');

    });

    it('should call submitRequest service and open error snackbar on error', () => {
      const mockFormValue = {
        currentPhone: '123-456-7890',
        desiredPhone: '098-765-4321',
        reason: 'Upgrade',
        contactEmail: 'test@example.com',
        contactPhone: '111-222-3333'
      };
      component.swapRequestForm.setValue(mockFormValue);
      (mockSwapService.submitRequest as jest.Mock).mockReturnValue(throwError(() => new Error('Test error')));

      component.onSubmit();

      expect(mockSwapService.submitRequest).toHaveBeenCalledWith(mockFormValue);
      expect(snackBar.open).toHaveBeenCalledWith('Error submitting request. Please try again.', 'Close', { duration: 5000 });
    });

    it('should open a snackbar with a validation message if the form is invalid', () => {
      component.onSubmit();

      expect(mockSwapService.submitRequest).not.toHaveBeenCalled();
      expect(snackBar.open).toHaveBeenCalledWith('Please fill in all required fields correctly.', 'Close', { duration: 5000 });
    });

    it('should reset the form after a successful submission', () => {
      const mockFormValue = {
        currentPhone: '123-456-7890',
        desiredPhone: '098-765-4321',
        reason: 'Upgrade',
        contactEmail: 'test@example.com',
        contactPhone: '111-222-3333'
      };
       component.swapRequestForm = fb.group({
        currentPhone: ['123-456-7890', Validators.required],
        desiredPhone: ['098-765-4321', Validators.required],
        reason: ['Upgrade'],
        contactEmail: ['test@example.com', [Validators.required, Validators.email]],
        contactPhone: ['111-222-3333', Validators.pattern('[- +()0-9]+')] // Basic phone validation
      });
      component.swapRequestForm.setValue(mockFormValue);
      (mockSwapService.submitRequest as jest.Mock).mockReturnValue(of({}));

      component.onSubmit();

      expect(mockSwapService.submitRequest).toHaveBeenCalledWith(mockFormValue);
      expect(snackBar.open).toHaveBeenCalledWith('Request submitted successfully!', 'Close', { duration: 3000 });
      // expect(component.swapRequestForm.value.currentPhone).toEqual('');
      // expect(component.swapRequestForm.value.desiredPhone).toEqual('');
      // expect(component.swapRequestForm.value.reason).toEqual('');
      // expect(component.swapRequestForm.value.contactEmail).toEqual('');
      // expect(component.swapRequestForm.value.contactPhone).toEqual('');

    });
  });

  describe('Form Control Getters', () => {
    it('should return the currentPhone form control', () => {
      const control = component.currentPhone;
      expect(control).toBeDefined();
    });

    it('should return the desiredPhone form control', () => {
      const control = component.desiredPhone;
      expect(control).toBeDefined();
    });

    it('should return the reason form control', () => {
      const control = component.reason;
      expect(control).toBeDefined();
    });

    it('should return the contactEmail form control', () => {
      const control = component.contactEmail;
      expect(control).toBeDefined();
    });

    it('should return the contactPhone form control', () => {
      const control = component.contactPhone;
      expect(control).toBeDefined();
    });
  });
});