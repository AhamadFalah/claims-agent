// Field option lists mirror the Attio `claims` object Select attributes
// defined in `Attio Schema Design.md`. Keep these in sync with the CRM schema.

export const COURIERS = ['Evri', 'DPD', 'Royal Mail', 'Yodel', 'Other'] as const;
export type Courier = (typeof COURIERS)[number];

export const CLAIM_TYPES = ['Lost', 'Damage'] as const;
export type ClaimType = (typeof CLAIM_TYPES)[number];

// Shape of the form's text state. The photo file is held separately
// (a File can't live cleanly in this record) and the values here map 1:1
// onto the multipart field names sent to the n8n webhook.
export interface ClaimFormValues {
  name: string;
  email: string;
  phone_number: string;
  order_number: string;
  courier: Courier | '';
  claim_type: ClaimType | '';
  parcel_count: string;
  tracking_number: string;
  additional_tracking: string;
  delivery_postcode: string;
  customer_comment: string;
  parcel_value: string;
}

export const INITIAL_VALUES: ClaimFormValues = {
  name: '',
  email: '',
  phone_number: '',
  order_number: '',
  courier: '',
  claim_type: '',
  parcel_count: '1',
  tracking_number: '',
  additional_tracking: '',
  delivery_postcode: '',
  customer_comment: '',
  parcel_value: '',
};

export type FormErrors = Partial<Record<keyof ClaimFormValues | 'photo', string>>;

export type SubmitState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | { status: 'success' }
  | { status: 'error'; message: string };
