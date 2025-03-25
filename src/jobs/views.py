from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Job
from .forms import JobForm

def job_list(request):
    jobs = Job.objects.filter(is_active=True)
    search_query = request.GET.get('search')
    job_type = request.GET.get('job_type')
    location = request.GET.get('location')
    experience_level = request.GET.get('experience_level')
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    if location:
        jobs = jobs.filter(location__icontains=location)
    if experience_level:
        jobs = jobs.filter(experience_level=experience_level)
    paginator = Paginator(jobs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'job_type': job_type,
        'location': location,
        'experience_level': experience_level,
    }
    return render(request, 'jobs/job_list.html', context)

def job_detail(request, slug):
    job = get_object_or_404(Job, slug=slug, is_active=True)
    context = {
        'job': job,
        'has_applied': job.applications.filter(applicant=request.user).exists() if request.user.is_authenticated else False,
    }
    return render(request, 'jobs/job_detail.html', context)

@login_required
def job_create(request):
    if not request.user.profile.is_employer:
        messages.error(request, 'Only employers can post jobs.')
        return redirect('job_list')
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = request.user
            job.save()
            messages.success(request, 'Job posted successfully!')
            return redirect('job_detail', slug=job.slug)
    else:
        form = JobForm()
    return render(request, 'jobs/job_form.html', {'form': form, 'title': 'Post a Job'})

@login_required
def job_edit(request, slug):
    job = get_object_or_404(Job, slug=slug)
    if job.employer != request.user:
        messages.error(request, 'You do not have permission to edit this job.')
        return redirect('job_detail', slug=job.slug)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            job = form.save()
            messages.success(request, 'Job updated successfully!')
            return redirect('job_detail', slug=job.slug)
    else:
        form = JobForm(instance=job)
    return render(request, 'jobs/job_form.html', {'form': form, 'title': 'Edit Job'})

@login_required
def job_delete(request, slug):
    job = get_object_or_404(Job, slug=slug)
    if job.employer != request.user:
        messages.error(request, 'You do not have permission to delete this job.')
        return redirect('job_detail', slug=job.slug)
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job deleted successfully!')
        return redirect('job_list')
    return render(request, 'jobs/job_confirm_delete.html', {'job': job})
