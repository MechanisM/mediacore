# This file is a part of MediaCore, Copyright 2009 Simple Station Inc.
#
# MediaCore is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MediaCore is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import simplejson as json
import shutil

from tg import config, request, response, tmpl_context
from tg.controllers import CUSTOM_CONTENT_TYPE
from sqlalchemy import orm, sql
from repoze.what.predicates import has_permission
from PIL import Image

from mediacore.lib.base import (BaseController, url_for, redirect,
    expose, expose_xhr, validate, paginate)
from mediacore.lib import helpers
from mediacore.model import (DBSession, fetch_row, get_available_slug,
    Podcast, Author, AuthorWithIP)
from mediacore.model.podcasts import create_podcast_stub
from mediacore.forms.admin import SearchForm, ThumbForm
from mediacore.forms.podcasts import PodcastForm


podcast_form = PodcastForm()
thumb_form = ThumbForm()

class PodcastadminController(BaseController):
    allow_only = has_permission('admin')

    @expose_xhr('mediacore.templates.admin.podcasts.index',
                'mediacore.templates.admin.podcasts.index-table')
    @paginate('podcasts', items_per_page=10)
    def index(self, page=1, **kw):
        """List podcasts with pagination.

        :param page: Page number, defaults to 1.
        :type page: int
        :rtype: Dict
        :returns:
            podcasts
                The list of :class:`~mediacore.model.podcasts.Podcast`
                instances for this page.
        """
        podcasts = DBSession.query(Podcast)\
            .options(orm.undefer('media_count'))\
            .order_by(Podcast.title)
        return dict(podcasts=podcasts)


    @expose('mediacore.templates.admin.podcasts.edit')
    def edit(self, id, **values):
        """Display the podcast forms for editing or adding.

        This page serves as the error_handler for every kind of edit action,
        if anything goes wrong with them they'll be redirected here.

        :param id: Podcast ID
        :type id: ``int`` or ``"new"``
        :param \*\*kwargs: Extra args populate the form for ``"new"`` podcasts
        :returns:
            podcast
                :class:`~mediacore.model.podcasts.Podcast` instance
            form
                :class:`~mediacore.forms.podcasts.PodcastForm` instance
            form_action
                ``str`` form submit url
            form_values
                ``dict`` form values
            thumb_form
                :class:`~mediacore.forms.admin.ThumbForm` instance
            thumb_action
                ``str`` form submit url

        """
        podcast = fetch_row(Podcast, id)

        explicit_values = dict(yes=True, clean=False)
        form_values = dict(
            slug = podcast.slug,
            title = podcast.title,
            subtitle = podcast.subtitle,
            author_name = podcast.author and podcast.author.name or None,
            author_email = podcast.author and podcast.author.email or None,
            description = podcast.description,
            details = dict(
                explicit = {True: 'yes', False: 'clean'}.get(podcast.explicit, 'no'),
                category = podcast.category,
                copyright = podcast.copyright,
                itunes_url = podcast.itunes_url,
                feedburner_url = podcast.feedburner_url,
            ),
        )
        form_values.update(values)

        thumb_form_errors = {}
        if tmpl_context.action == 'save_thumb':
            thumb_form_errors = tmpl_context.form_errors

        return dict(
            podcast = podcast,
            form = podcast_form,
            form_action = url_for(action='save'),
            form_values = form_values,
            thumb_form = thumb_form,
            thumb_action = url_for(action='save_thumb'),
            thumb_form_errors = thumb_form_errors,
        )


    @expose()
    @validate(podcast_form, error_handler=edit)
    def save(self, id, slug, title, subtitle, author_name, author_email,
             description, details, delete=None, **kwargs):
        """Save changes or create a new :class:`~mediacore.model.podcasts.Podcast` instance.

        Form handler the :meth:`edit` action and the
        :class:`~mediacore.forms.podcasts.PodcastForm`.

        Redirects back to :meth:`edit` after successful editing
        and :meth:`index` after successful deletion.

        """
        podcast = fetch_row(Podcast, id)

        if delete:
            DBSession.delete(podcast)
            DBSession.flush()
            redirect(action='index', id=None)

        podcast.slug = get_available_slug(Podcast, slug, podcast)
        podcast.title = title
        podcast.subtitle = subtitle
        podcast.author = Author(author_name, author_email)
        podcast.description = helpers.clean_admin_xhtml(description)
        podcast.copyright = details['copyright']
        podcast.category = details['category']
        podcast.itunes_url = details['itunes_url']
        podcast.feedburner_url = details['feedburner_url']
        podcast.explicit = {'yes': True, 'clean': False}.get(details['explicit'], None)

        DBSession.add(podcast)
        DBSession.flush()
        redirect(action='edit', id=podcast.id)


    @expose(content_type=CUSTOM_CONTENT_TYPE)
    @validate(thumb_form, error_handler=edit)
    def save_thumb(self, id, thumb, **values):
        """Save a thumbnail uploaded with :class:`~mediacore.forms.admin.ThumbForm`.

        :param id: Media ID. If ``"new"`` a new Media stub is created with
            :func:`~mediacore.model.media.create_podcast_stub`.
        :type id: ``int`` or ``"new"``
        :param file: The uploaded file
        :type file: :class:`cgi.FieldStorage` or ``None``
        :rtype: JSON dict
        :returns:
            success
                bool
            message
                Error message, if unsuccessful
            id
                The :attr:`~mediacore.model.podcasts.Podcast.id` which is
                important if a new podcast has just been created.

        .. note::

            This method returns incorrect Content-Type headers under
            some circumstances. It should be ``application/json``, but
            sometimes ``text/plain`` is used instead.

            This is because this method is used from the flash based
            uploader; Swiff.Uploader (which we use) uses Flash's
            FileReference.upload() method, which doesn't allow
            overriding the default HTTP headers.

            On windows, the default Accept header is "text/\*". This
            means that it won't accept "application/json". Rather than
            throw a 406 Not Acceptable response, or worse, a 500 error,
            we've chosen to return an incorrect ``text/plain`` type.

        """
        if id == 'new':
            podcast = create_podcast_stub()
        else:
            podcast = fetch_row(Podcast, id)

        try:
            # Create jpeg thumbs
            img = Image.open(thumb.file)

            if id == 'new':
                DBSession.add(podcast)
                DBSession.flush()

            # TODO: Allow other formats?
            for key, xy in config.thumb_sizes[podcast._thumb_dir].iteritems():
                thumb_path = helpers.thumb_path(podcast, key)
                thumb_img = helpers.resize_thumb(img, xy)
                thumb_img.save(thumb_path)

            # Backup the original image just for kicks
            backup_type = os.path.splitext(thumb.filename)[1].lower()[1:]
            backup_path = helpers.thumb_path(podcast, 'orig', ext=backup_type)
            backup_file = open(backup_path, 'w+b')
            thumb.file.seek(0)
            shutil.copyfileobj(thumb.file, backup_file)
            thumb.file.close()
            backup_file.close()

            success = True
            message = None
        except IOError, e:
            success = False
            message = 'Unsupported image type'
        except Exception, e:
            success = False
            message = e.message

        response.headers['Content-Type'] = helpers.best_json_content_type()
        return json.dumps(dict(
            success = success,
            message = message,
            id = podcast.id,
        ))
