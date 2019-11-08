
import logging
import os
import re
from textwrap import dedent
import hashlib
import urllib.parse
import random

from datetime import timedelta, datetime
from django.contrib import messages
from django import template, forms

from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.paginator import Paginator
from django.db.models import Q,Count
from django.template import defaultfilters
from django.utils.safestring import mark_safe

from biostar.recipes import auth, util, const
from biostar.recipes.models import Job, make_html, Project, Data, Analysis, Access, SnippetType, Snippet


logger = logging.getLogger("engine")
register = template.Library()

JOB_COLORS = {Job.SPOOLED: "spooled",
              Job.ERROR: "errored", Job.QUEUED: "queued",
              Job.RUNNING: "running", Job.COMPLETED: "completed"
              }
DATA_COLORS = {
    Data.PENDING: "teal", Data.READY: "green", Data.ERROR: "red"
}


@register.simple_tag
def randparam():
    "Append to URL to bypass server caching of CSS or JS files"
    return f"?randval={random.randint(1, 10000000)}" if settings.DEBUG else ""


@register.filter
def mask_path(val='', obj={}):

    is_path = obj.get('display') == const.UPLOAD
    if is_path:
        return os.path.basename(str(val)) if val else ''

    return val


@register.filter
def time_ago(date):
    pluralize = lambda value, word: f"{value} {word}s" if value > 1 else f'{value} {word}'
    if not date:
        return ''
    delta = util.now() - date
    if delta < timedelta(minutes=1):
        return 'just now'
    elif delta < timedelta(hours=1):
        unit = pluralize(delta.seconds // 60, "minute")
    elif delta < timedelta(days=1):
        unit = pluralize(delta.seconds // 3600, "hour")
    elif delta < timedelta(days=30):
        unit = pluralize(delta.days, "day")
    elif delta < timedelta(days=90):
        unit = pluralize(int(delta.days / 7), "week")
    elif delta < timedelta(days=730):
        unit = pluralize(int(delta.days / 30), "month")
    else:
        diff = delta.days / 365.0
        unit = '%0.1f years' % diff
    return "%s ago" % unit

def join(*args):
    return os.path.abspath(os.path.join(*args))

@register.filter
def bignum(number):
    "Reformats numbers with qualifiers as K"
    try:
        value = float(number) / 1000.0
        if value > 10:
            return "%0.fk" % value
        elif value > 1:
            return "%0.1fk" % value
    except ValueError as exc:
        pass
    return str(number)


@register.simple_tag()
def user_score(user):
    score = user.profile.score * 10
    return score


@register.inclusion_tag('widgets/user_icon.html')
def user_icon(user):
    score = user_score(user)
    context = dict(user=user, score=score)
    return context


@register.inclusion_tag('widgets/list_view.html', takes_context=True)
def list_projects(context, target):

    user = context["request"].user
    request = context["request"]
    projects = auth.get_project_list(user=target)

    # Don't show private projects non owners
    if user != target:
        projects = projects.exclude(privacy=Project.PRIVATE)

    projects = projects.annotate(data_count=Count('data', distinct=True, filter=Q(deleted=False)),
                                 job_count=Count('job', distinct=True, filter=Q(deleted=False)),
                                 recipe_count=Count('analysis', distinct=True, filter=Q(deleted=False)),
                                 )
    projects = projects.order_by("-rank", "-lastedit_date")

    return dict(projects=projects, user=target)


@register.simple_tag
def gravatar(user, size=80):
    style = "retro"
    if user.is_anonymous or user.profile.is_suspended:
        # Removes spammy images for suspended users
        # email = 'suspended@biostars.org'.encode('utf8')
        style = "monsterid"
    else:
        if user.profile.is_moderator:
            style = "robohash"
        email = user.email.encode('utf8')

    hash = hashlib.md5(email).hexdigest()

    gravatar_url = "https://secure.gravatar.com/avatar/%s?" % hash
    gravatar_url += urllib.parse.urlencode({
        's': str(size),
        'd': style,
    }
    )
    return gravatar_url


@register.filter
def highlight(source, target):

    # Look for case insensitive matches in the source
    highlighting = re.search(f"(?i){target}", source)

    target = highlighting.group() if highlighting else target

    # Highlight the target
    highlighted = mark_safe(f"<div class='match'>{target}</div>")

    return source.replace(target, highlighted)


@register.simple_tag
def get_qiime2view_link(file_serve_url):
    port = f':{settings.HTTP_PORT}' if settings.HTTP_PORT else ''
    site = f"{settings.PROTOCOL}://{settings.SITE_DOMAIN}{port}"

    full_url = site + file_serve_url

    qiime_link = util.qiime2view_link(full_url)

    return qiime_link


@register.inclusion_tag('widgets/list_view.html', takes_context=True)
def list_view(context, projects=None, data_list=None, recipe_list=None, job_list=None):
    request = context["request"]
    user = request.user
    return dict(projects=projects, user=user, data_list=data_list, recipe_list=recipe_list,
                job_list=job_list, request=request)


@register.inclusion_tag('widgets/paste.html', takes_context=True)
def paste(context, project, current=""):

    request = context["request"]
    clipboard = request.session.get(settings.CLIPBOARD_NAME, {})
    board = clipboard.get(current, [])

    clipboard_count = len(board) if request.user.is_authenticated else 0

    extra_context = dict(clipboard_count=clipboard_count, project=project, current=current, board=board, context=context)
    context.update(extra_context)
    return context


@register.filter
def is_checkbox(field):
    "Check if current field is a checkbox"

    try:
        if field.field.widget.input_type == "checkbox":
            return True
    except Exception as exc:
        logger.error(exc)

    return False


@register.filter
def is_qiime_archive(file=None):
    filename = file if isinstance(file, str) else file.path

    return filename.endswith(".qza") or filename.endswith(".qzv")


@register.simple_tag
def privacy_label(project):
    label = mark_safe(f'<span class ="ui label">{project.get_privacy_display()}</span>')
    return label


@register.inclusion_tag('widgets/authorization_required.html', takes_context=True)
def security_label(context, analysis):
    context.update(dict(analysis=analysis))

    return context


@register.simple_tag
def full_url():
    if settings.HTTP_PORT:
        return f"{settings.PROTOCOL}://{settings.SITE_DOMAIN}:{settings.HTTP_PORT}"
    else:
        return f"{settings.PROTOCOL}://{settings.SITE_DOMAIN}"

@register.simple_tag
def job_color(job):
    """
    Returns a color based on job status.
    """
    try:
        if isinstance(job, Job):
            return JOB_COLORS.get(job.state, "")
    except Exception as exc:
        logger.error(exc)
        return ''

@register.simple_tag
def activate(value1, value2):
    """
    Returns a color based on job status.
    """
    return "active" if value1 == value2 else ''


@register.simple_tag
def data_color(data):
    "Return a color based on data status."

    return DATA_COLORS.get(data.state, "")


@register.simple_tag
def type_label(data):
    if data.type:
        label = lambda x: f"<span class='ui label' > {x} </span>"
        types = [label(t) for t in data.type.split(',')]
        return mark_safe(''.join(types))
    return ""


@register.simple_tag
def state_label(data, error_only=False):
    label = f'<span class="ui { DATA_COLORS.get(data.state, "") } label"> {data.get_state_display()} </span>'

    # Error produce error only.
    if error_only and data.state not in (Data.ERROR, Data.PENDING):
        label = ""

    return mark_safe(label)


@register.simple_tag
def img(obj):
    """
    Returns the image associated with the object or a placeholder
    """
    if obj.image:
        return obj.image.url
    else:
        return static("images/placeholder.png")


@register.inclusion_tag('widgets/show_messages.html')
def show_messages(messages):
    """
    Renders the messages
    """
    return dict(messages=messages)


@register.inclusion_tag('widgets/project_title.html', takes_context=True)
def project_title(context, project):
    """
    Returns a label for project.
    """
    return dict(project=project)


@register.inclusion_tag('widgets/recipe_form.html')
def recipe_form(form):
    """
    Renders a recipe form.
    """
    return dict(form=form)


@register.inclusion_tag('widgets/interface_options.html')
def interface_options():
    return dict()


@register.simple_tag
def image_field(default=''):
    if default:
        image_field = forms.ImageField(required=False, default=default)
    else:
        image_field = forms.ImageField(required=False)
    image_field.widget.attrs.update({'id': 'image'})
    placeholder = os.path.join(settings.STATIC_ROOT, 'images', 'placeholder.png')
    image_widget = image_field.widget.render('image', value=placeholder)

    return mark_safe(image_widget)


@register.inclusion_tag('widgets/snippet_list.html', takes_context=True)
def snippet_list(context):

    user = context['request'].user
    if user.is_anonymous:
        command_types = SnippetType.objects.filter(default=True).order_by('-pk')
    else:
        command_types = SnippetType.objects.filter(Q(owner=user) | Q(default=True)).order_by('-pk')

    extra_context = dict(command_types=command_types)
    context.update(extra_context)
    return context


@register.inclusion_tag('widgets/snippet.html', takes_context=True)
def snippet_item(context, snippet):

    extra_context = dict(snippet=snippet)
    context.update(extra_context)
    return context


@register.inclusion_tag('widgets/snippet_type.html', takes_context=True)
def snippet_type(context, snip_type):
    extra_context = dict(type=snip_type)
    context.update(extra_context)
    return context


@register.simple_tag
def get_snippets(user, snip_type):
    if user.is_authenticated:
        snippets = snip_type.snippet_set.filter(Q(owner=user) | Q(default=True))
    else:
        snippets = snip_type.snippet_set.filter(default=True)
    return snippets



@register.inclusion_tag('widgets/json_field.html')
def json_field(json_text):

    context = dict(json_text=json_text)
    return context


@register.inclusion_tag('widgets/template_field.html')
def template_field(tmpl):

    context = dict(template=tmpl)
    return context


@register.inclusion_tag('widgets/created_by.html')
def created_by(date, user=None, prefix="updated"):
    """
    Renders a created by link
    """
    return dict(date=date, user=user, prefix=prefix)

@register.inclusion_tag('widgets/access_form.html')
def access_form(project, user, form):
    """
    Generates an access form.
    """

    return dict(project=project, user=user, form=form)


@register.inclusion_tag('widgets/job_elapsed.html')
def job_minutes(job):

    check_back = ''
    # Add a tag to check a state change every ~5 seconds and update tag
    if job.state in [Job.SPOOLED, Job.RUNNING, Job.QUEUED]:
        check_back = 'check_back'

    return dict(job=job, check_back=check_back)


@register.simple_tag
def size_label(data):
    """
    Returns a label for data sizes.
    """

    size = f"{defaultfilters.filesizeformat(data.size)}"
    return mark_safe(f"<span class='ui mini label'>{size}</span>")


@register.simple_tag
def get_access_label(project, user):

    if project.owner.id == user.id:
        return 'Owner Access'

    # Need to check  anonymous users before access
    if user.is_anonymous:
        return 'Public Access'

    access = Access.objects.filter(project=project, user=user).first()

    # If the access is not read, write, or share
    # and the project is public, then it is seen as 'Readable'
    if not access and project.is_public:
        return 'Public Access'

    access_str = access.get_access_display() if access else 'No Access'

    return access_str


def file_listing(root, limit=None):
    # This will collect the valid filepaths.
    paths = []
    count = 0
    try:
        # Walk the filesystem and collect all files.
        for fpath, fdirs, fnames in os.walk(root, followlinks=True):
            paths.extend([join(fpath, fname) for fname in fnames])
            count += 1
            if limit and count >= limit:
                break

        # Image extension types.
        IMAGE_EXT = {"png", "jpg", "gif", "jpeg"}

        # Add more metadata to each path.
        def transform(path):
            tstamp = os.stat(path).st_mtime
            size = os.stat(path).st_size
            rel_path = os.path.relpath(path, root)
            elems = os.path.split(rel_path)
            dir_names = elems[:-1]
            if dir_names[0] == '':
                dir_names = []
            last_name = elems[-1]
            is_image = last_name.split(".")[-1] in IMAGE_EXT
            return rel_path, dir_names, last_name, tstamp, size, is_image

        # Transform the paths.
        paths = map(transform, paths)

        # Sort by the tuple fields..
        paths = sorted(paths)

    except Exception as exc:
        logging.error(exc)
        paths = []

    return paths


def listing(root):
    paths = []

    try:
        paths = os.listdir(root)

        def transform(path):
            path = os.path.join(root, path)
            tstamp = os.stat(path).st_mtime
            size = os.stat(path).st_size
            rel_path = os.path.relpath(path, settings.IMPORT_ROOT_DIR)
            is_dir = os.path.isdir(path)
            basename = os.path.basename(path)
            return rel_path, tstamp, size, is_dir, basename

        paths = map(transform, paths)
        # Sort files by timestamps
        paths = sorted(paths, key=lambda x: x[1], reverse=True)

    except Exception as exc:
        logging.error(exc)

    return paths


@register.inclusion_tag('widgets/files_list.html', takes_context=True)
def files_list(context, rel_path):
    # Limit to the first 100 files.
    root = os.path.abspath(os.path.join(settings.IMPORT_ROOT_DIR, rel_path))
    paths = listing(root=root)
    user = context['request'].user
    return dict(paths=paths, user=user, root=root)


@register.inclusion_tag('widgets/directory_list.html', takes_context=True)
def directory_list(context, obj):
    """
    Generates an HTML listing for files in a directory.
    """

    # Starting location.
    root = obj.get_data_dir()

    # The serve url depends on data type..
    serve_url = "job_serve" if isinstance(obj, Job) else "data_serve"
    copy_url = "job_file_copy" if isinstance(obj, Job) else "data_file_copy"

    paths = file_listing(root=root)

    return dict(paths=paths, obj=obj, serve_url=serve_url, copy_url=copy_url, user=context["request"].user)


@register.inclusion_tag('widgets/form_errors.html')
def form_errors(form):
    """
    Turns form errors into a data structure
    """
    try:
        errorlist = [('', message) for message in form.non_field_errors()]

        for field in form:
            for error in field.errors:
                errorlist.append((f'{field.name}:', error))
    except Exception:
        errorlist = []

    context = dict(errorlist=errorlist)

    return context


@register.filter
def markdown(text):
    """
    Generates HTML from a markdown value.
    """
    if not text:
        return ''
    text = dedent(text)
    html = make_html(text)
    return mark_safe(html)


@register.inclusion_tag("widgets/menubar.html", takes_context=True)
def menubar(context, request=None, with_search=True):
    user = context.request.user
    context.update(dict(user=user, request=request, with_search=with_search))

    return context
