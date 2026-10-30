from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PatientForm
from .models import Patient
from .services.ai_service import REMARKS_UNAVAILABLE, get_health_remarks

# If any of these fields change on edit, the AI remarks must be regenerated.
AI_FIELDS = {'date_of_birth', 'glucose', 'haemoglobin', 'cholesterol'}


def _generate_remarks(patient):
    return get_health_remarks(
        patient.date_of_birth, patient.glucose,
        patient.haemoglobin, patient.cholesterol,
    )


def _notify_remarks(request, patient, action):
    if patient.remarks == REMARKS_UNAVAILABLE:
        messages.warning(
            request,
            f'{patient.full_name} was {action}, but the AI remarks are unavailable. '
            'Use the Retry button in the list.')
    else:
        messages.success(request, f'{patient.full_name} was {action} successfully.')


def patient_list(request):
    """READ: show all records."""
    return render(request, 'patients/list.html', {
        'patients': Patient.objects.all(),
        'unavailable': REMARKS_UNAVAILABLE,
    })


def patient_create(request):
    """CREATE: validate, call the AI, then save."""
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():  # AI is called only after validation passes
            patient = form.save(commit=False)
            patient.remarks = _generate_remarks(patient)
            patient.save()
            _notify_remarks(request, patient, 'added')
            return redirect('patient_list')
        messages.error(request, 'The record was not saved. Please fix the errors below.')
    else:
        form = PatientForm()
    return render(request, 'patients/form.html', {'form': form, 'title': 'Add patient'})


def patient_edit(request, pk):
    """UPDATE: call the AI again only if the blood values or DOB changed."""
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            needs_ai = bool(AI_FIELDS & set(form.changed_data))
            patient = form.save(commit=False)
            if needs_ai or not patient.remarks or patient.remarks == REMARKS_UNAVAILABLE:
                patient.remarks = _generate_remarks(patient)
            patient.save()
            _notify_remarks(request, patient, 'updated')
            return redirect('patient_list')
        messages.error(request, 'The record was not updated. Please fix the errors below.')
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patients/form.html', {'form': form, 'title': 'Edit patient'})


def patient_delete(request, pk):
    """DELETE: ask for confirmation first, delete on POST."""
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        name = patient.full_name
        patient.delete()
        messages.success(request, f'{name} was deleted.')
        return redirect('patient_list')
    return render(request, 'patients/confirm_delete.html', {'patient': patient})


@require_POST
def patient_retry_remarks(request, pk):
    """Re-run the AI for a record whose remarks are unavailable."""
    patient = get_object_or_404(Patient, pk=pk)
    patient.remarks = _generate_remarks(patient)
    patient.save()
    _notify_remarks(request, patient, 'refreshed')
    return redirect('patient_list')