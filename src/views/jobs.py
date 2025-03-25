from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from src.job_posting.models import Job
from src.forms import JobForm

def job_list(request):
    jobs = Job.objects.filter(is_active=True)
    query = request.GET.get('q')
    job_type = request.GET.get('type')
    experience = request.GET.get('experience')

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(company__icontains=query) |
            Q(description__icontains=query)
        )

    if job_type:
        jobs = jobs.filter(job_type=job_type)

    if experience:
        jobs = jobs.filter(experience_level=experience)

    paginator = Paginator(jobs, 10)
    page = request.GET.get('page')
    jobs = paginator.get_page(page)

    context = {
        'jobs': jobs,
        'query': query,
        'job_type': job_type,
        'experience': experience,
    }
    return render(request, 'jobs/job_list.html', context)

def job_detail(request, slug):
    job = get_object_or_404(Job, slug=slug)
    return render(request, 'jobs/job_detail.html', {'job': job})

@login_required
def job_create(request):
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
    return render(request, 'jobs/job_form.html', {'form': form, 'title': 'Create Job'})

@login_required
def job_edit(request, slug):
    job = get_object_or_404(Job, slug=slug)
    if request.user != job.posted_by:
        messages.error(request, 'You do not have permission to edit this job posting.')
        return redirect('job_detail', slug=slug)

    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            job = form.save()
            messages.success(request, 'Job posting updated successfully.')
            return redirect('job_detail', slug=job.slug)
    else:
        form = JobForm(instance=job)
    return render(request, 'jobs/job_form.html', {'form': form, 'title': 'Edit Job'})

@login_required
def job_delete(request, slug):
    job = get_object_or_404(Job, slug=slug)
    if request.user != job.posted_by:
        messages.error(request, 'You do not have permission to delete this job posting.')
        return redirect('job_detail', slug=slug)

    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job posting deleted successfully.')
        return redirect('job_list')
    return render(request, 'jobs/job_confirm_delete.html', {'job': job})
