from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Application, Document
from .forms import ApplicationForm, DocumentForm
from src.jobs.models import Job

@login_required
def application_list(request):
    applications = Application.objects.filter(applicant=request.user)
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'applications/application_list.html', {'page_obj': page_obj})

@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if application.applicant != request.user and application.job.employer != request.user:
        messages.error(request, 'You do not have permission to view this application.')
        return redirect('application_list')
    return render(request, 'applications/application_detail.html', {'application': application})

@login_required
def application_create(request, job_slug):
    job = get_object_or_404(Job, slug=job_slug, is_active=True)

    # Check if user has already applied
    if job.applications.filter(applicant=request.user).exists():
        messages.error(request, 'You have already applied for this job.')
        return redirect('job_detail', slug=job_slug)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = request.user
            application.save()
            messages.success(request, 'Application submitted successfully!')
            return redirect('application_detail', pk=application.pk)
    else:
        form = ApplicationForm()

    return render(request, 'applications/application_form.html', {
        'form': form,
        'job': job,
        'title': 'Apply for Job'
    })

@login_required
def application_edit(request, pk):
    application = get_object_or_404(Application, pk=pk)

    if application.applicant != request.user:
        messages.error(request, 'You do not have permission to edit this application.')
        return redirect('application_list')

    if application.status != 'draft':
        messages.error(request, 'You can only edit draft applications.')
        return redirect('application_detail', pk=pk)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES, instance=application)
        if form.is_valid():
            application = form.save()
            messages.success(request, 'Application updated successfully!')
            return redirect('application_detail', pk=application.pk)
    else:
        form = ApplicationForm(instance=application)

    return render(request, 'applications/application_form.html', {
        'form': form,
        'application': application,
        'title': 'Edit Application'
    })

@login_required
def document_create(request, application_pk):
    application = get_object_or_404(Application, pk=application_pk)

    if application.applicant != request.user:
        messages.error(request, 'You do not have permission to add documents to this application.')
        return redirect('application_list')

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.application = application
            document.save()
            messages.success(request, 'Document added successfully!')
            return redirect('application_detail', pk=application_pk)
    else:
        form = DocumentForm()

    return render(request, 'applications/document_form.html', {
        'form': form,
        'application': application,
        'title': 'Add Document'
    })

@login_required
def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk)
    application_pk = document.application.pk

    if document.application.applicant != request.user:
        messages.error(request, 'You do not have permission to delete this document.')
        return redirect('application_detail', pk=application_pk)

    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Document deleted successfully!')
        return redirect('application_detail', pk=application_pk)

    return render(request, 'applications/document_confirm_delete.html', {
        'document': document,
        'application': document.application
    })
