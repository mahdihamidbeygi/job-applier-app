from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from src.job_posting.models import Job
from src.job_application.models import Application
from src.forms import ApplicationForm

@login_required
def application_list(request):
    applications = Application.objects.filter(applicant=request.user)
    paginator = Paginator(applications, 10)
    page = request.GET.get('page')
    applications = paginator.get_page(page)
    return render(request, 'applications/application_list.html', {'applications': applications})

@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if request.user != application.applicant and request.user != application.job.posted_by:
        messages.error(request, 'You do not have permission to view this application.')
        return redirect('application_list')
    return render(request, 'applications/application_detail.html', {'application': application})

@login_required
def application_create(request, job_slug):
    job = get_object_or_404(Job, slug=job_slug, is_active=True)
    if Application.objects.filter(job=job, applicant=request.user).exists():
        messages.error(request, 'You have already applied for this job.')
        return redirect('job_detail', slug=job_slug)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = request.user
            application.save()
            messages.success(request, 'Application submitted successfully.')
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
    if request.user != application.applicant:
        messages.error(request, 'You do not have permission to edit this application.')
        return redirect('application_list')

    if application.status != 'draft':
        messages.error(request, 'You cannot edit a submitted application.')
        return redirect('application_detail', pk=pk)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES, instance=application)
        if form.is_valid():
            application = form.save()
            messages.success(request, 'Application updated successfully.')
            return redirect('application_detail', pk=application.pk)
    else:
        form = ApplicationForm(instance=application)
    return render(request, 'applications/application_form.html', {
        'form': form,
        'job': application.job,
        'title': 'Edit Application'
    })

@login_required
def application_submit(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if request.user != application.applicant:
        messages.error(request, 'You do not have permission to submit this application.')
        return redirect('application_list')

    if application.submit():
        messages.success(request, 'Application submitted successfully.')
    else:
        messages.error(request, 'This application has already been submitted.')
    return redirect('application_detail', pk=pk)

@login_required
def application_delete(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if request.user != application.applicant:
        messages.error(request, 'You do not have permission to delete this application.')
        return redirect('application_list')

    if request.method == 'POST':
        application.delete()
        messages.success(request, 'Application deleted successfully.')
        return redirect('application_list')
    return render(request, 'applications/application_confirm_delete.html', {'application': application})
