from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import JobForm, ApplicationForm, UserRegistrationForm
from .job_posting.models import Job
from .job_application.models import Application

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

def job_list(request):
    jobs = Job.objects.filter(is_active=True).order_by('-created_at')

    # Search functionality
    query = request.GET.get('q')
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(company__icontains=query) |
            Q(location__icontains=query) |
            Q(description__icontains=query)
        )

    # Filter functionality
    job_type = request.GET.get('job_type')
    if job_type:
        jobs = jobs.filter(job_type=job_type)

    experience_level = request.GET.get('experience_level')
    if experience_level:
        jobs = jobs.filter(experience_level=experience_level)

    # Pagination
    paginator = Paginator(jobs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'jobs/job_list.html', {
        'page_obj': page_obj,
        'query': query,
        'job_type': job_type,
        'experience_level': experience_level,
    })

def job_detail(request, slug):
    job = get_object_or_404(Job, slug=slug, is_active=True)
    return render(request, 'jobs/job_detail.html', {'job': job})

@login_required
def job_create(request):
    if not request.user.profile.is_employer:
        messages.error(request, 'Only employers can create job postings.')
        return redirect('job_list')

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.save()
            messages.success(request, 'Job posting created successfully.')
            return redirect('job_detail', slug=job.slug)
    else:
        form = JobForm()
    return render(request, 'jobs/job_form.html', {'form': form, 'title': 'Create Job Posting'})

@login_required
def job_edit(request, slug):
    job = get_object_or_404(Job, slug=slug, posted_by=request.user)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job posting updated successfully.')
            return redirect('job_detail', slug=job.slug)
    else:
        form = JobForm(instance=job)
    return render(request, 'jobs/job_form.html', {'form': form, 'title': 'Edit Job Posting'})

@login_required
def job_delete(request, slug):
    job = get_object_or_404(Job, slug=slug, posted_by=request.user)
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job posting deleted successfully.')
        return redirect('job_list')
    return render(request, 'jobs/job_confirm_delete.html', {'job': job})

@login_required
def application_create(request, job_slug):
    job = get_object_or_404(Job, slug=job_slug, is_active=True)
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
        'title': f'Apply for {job.title}'
    })

@login_required
def application_list(request):
    if request.user.profile.is_employer:
        applications = Application.objects.filter(job__posted_by=request.user)
    else:
        applications = Application.objects.filter(applicant=request.user)

    applications = applications.order_by('-created_at')
    return render(request, 'applications/application_list.html', {
        'applications': applications,
        'title': 'My Applications'
    })

def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if not (request.user == application.applicant or request.user == application.job.posted_by):
        messages.error(request, 'You do not have permission to view this application.')
        return redirect('application_list')
    return render(request, 'applications/application_detail.html', {'application': application})
