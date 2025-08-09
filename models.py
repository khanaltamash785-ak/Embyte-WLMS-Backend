# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class WpActionschedulerActions(models.Model):
    action_id = models.BigAutoField(primary_key=True)
    hook = models.CharField(max_length=191)
    status = models.CharField(max_length=20)
    scheduled_date_gmt = models.DateTimeField(blank=True, null=True)
    scheduled_date_local = models.DateTimeField(blank=True, null=True)
    priority = models.PositiveIntegerField()
    args = models.CharField(max_length=191, blank=True, null=True)
    schedule = models.TextField(blank=True, null=True)
    group_id = models.PositiveBigIntegerField()
    attempts = models.IntegerField()
    last_attempt_gmt = models.DateTimeField(blank=True, null=True)
    last_attempt_local = models.DateTimeField(blank=True, null=True)
    claim_id = models.PositiveBigIntegerField()
    extended_args = models.CharField(max_length=8000, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_actionscheduler_actions'


class WpActionschedulerClaims(models.Model):
    claim_id = models.BigAutoField(primary_key=True)
    date_created_gmt = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_actionscheduler_claims'


class WpActionschedulerGroups(models.Model):
    group_id = models.BigAutoField(primary_key=True)
    slug = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'wp_actionscheduler_groups'


class WpActionschedulerLogs(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    action_id = models.PositiveBigIntegerField()
    message = models.TextField()
    log_date_gmt = models.DateTimeField(blank=True, null=True)
    log_date_local = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_actionscheduler_logs'


class WpAioseoCache(models.Model):
    id = models.BigAutoField(primary_key=True)
    key = models.CharField(unique=True, max_length=80)
    value = models.TextField()
    expiration = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'wp_aioseo_cache'


class WpAioseoNotifications(models.Model):
    id = models.BigAutoField(primary_key=True)
    slug = models.CharField(unique=True, max_length=13)
    addon = models.CharField(max_length=64, blank=True, null=True)
    title = models.TextField()
    content = models.TextField()
    type = models.CharField(max_length=64)
    level = models.TextField()
    notification_id = models.PositiveBigIntegerField(blank=True, null=True)
    notification_name = models.CharField(max_length=255, blank=True, null=True)
    start = models.DateTimeField(blank=True, null=True)
    end = models.DateTimeField(blank=True, null=True)
    button1_label = models.CharField(max_length=255, blank=True, null=True)
    button1_action = models.CharField(max_length=255, blank=True, null=True)
    button2_label = models.CharField(max_length=255, blank=True, null=True)
    button2_action = models.CharField(max_length=255, blank=True, null=True)
    dismissed = models.IntegerField()
    new = models.IntegerField()
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'wp_aioseo_notifications'


class WpAioseoPosts(models.Model):
    id = models.BigAutoField(primary_key=True)
    post_id = models.PositiveBigIntegerField()
    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    keywords = models.TextField(blank=True, null=True)
    keyphrases = models.TextField(blank=True, null=True)
    page_analysis = models.TextField(blank=True, null=True)
    primary_term = models.TextField(blank=True, null=True)
    canonical_url = models.TextField(blank=True, null=True)
    og_title = models.TextField(blank=True, null=True)
    og_description = models.TextField(blank=True, null=True)
    og_object_type = models.CharField(max_length=64, blank=True, null=True)
    og_image_type = models.CharField(max_length=64, blank=True, null=True)
    og_image_url = models.TextField(blank=True, null=True)
    og_image_width = models.IntegerField(blank=True, null=True)
    og_image_height = models.IntegerField(blank=True, null=True)
    og_image_custom_url = models.TextField(blank=True, null=True)
    og_image_custom_fields = models.TextField(blank=True, null=True)
    og_video = models.CharField(max_length=255, blank=True, null=True)
    og_custom_url = models.TextField(blank=True, null=True)
    og_article_section = models.TextField(blank=True, null=True)
    og_article_tags = models.TextField(blank=True, null=True)
    twitter_use_og = models.IntegerField(blank=True, null=True)
    twitter_card = models.CharField(max_length=64, blank=True, null=True)
    twitter_image_type = models.CharField(max_length=64, blank=True, null=True)
    twitter_image_url = models.TextField(blank=True, null=True)
    twitter_image_custom_url = models.TextField(blank=True, null=True)
    twitter_image_custom_fields = models.TextField(blank=True, null=True)
    twitter_title = models.TextField(blank=True, null=True)
    twitter_description = models.TextField(blank=True, null=True)
    seo_score = models.IntegerField()
    schema = models.TextField(blank=True, null=True)
    schema_type = models.CharField(max_length=20, blank=True, null=True)
    schema_type_options = models.TextField(blank=True, null=True)
    pillar_content = models.IntegerField(blank=True, null=True)
    robots_default = models.IntegerField()
    robots_noindex = models.IntegerField()
    robots_noarchive = models.IntegerField()
    robots_nosnippet = models.IntegerField()
    robots_nofollow = models.IntegerField()
    robots_noimageindex = models.IntegerField()
    robots_noodp = models.IntegerField()
    robots_notranslate = models.IntegerField()
    robots_max_snippet = models.IntegerField(blank=True, null=True)
    robots_max_videopreview = models.IntegerField(blank=True, null=True)
    robots_max_imagepreview = models.CharField(max_length=20, blank=True, null=True)
    images = models.TextField(blank=True, null=True)
    image_scan_date = models.DateTimeField(blank=True, null=True)
    priority = models.FloatField(blank=True, null=True)
    frequency = models.TextField(blank=True, null=True)
    videos = models.TextField(blank=True, null=True)
    video_thumbnail = models.TextField(blank=True, null=True)
    video_scan_date = models.DateTimeField(blank=True, null=True)
    local_seo = models.TextField(blank=True, null=True)
    limit_modified_date = models.IntegerField()
    options = models.TextField(blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'wp_aioseo_posts'


class WpBadgeosAchievements(models.Model):
    entry_id = models.AutoField(primary_key=True)
    id = models.IntegerField(db_column='ID', blank=True, null=True)  # Field name made lowercase.
    sub_nom_id = models.IntegerField(blank=True, null=True)
    post_type = models.CharField(max_length=100, blank=True, null=True)
    achievement_title = models.TextField(blank=True, null=True)
    rec_type = models.CharField(max_length=10, blank=True, null=True)
    points = models.IntegerField(blank=True, null=True)
    point_type = models.CharField(max_length=50, blank=True, null=True)
    user_id = models.IntegerField(blank=True, null=True)
    this_trigger = models.CharField(max_length=100, blank=True, null=True)
    image = models.CharField(max_length=50, blank=True, null=True)
    site_id = models.IntegerField(blank=True, null=True)
    actual_date_earned = models.DateTimeField(blank=True, null=True)
    date_earned = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_badgeos_achievements'


class WpBadgeosPoints(models.Model):
    achievement_id = models.IntegerField(blank=True, null=True)
    credit_id = models.IntegerField(blank=True, null=True)
    step_id = models.IntegerField(blank=True, null=True)
    user_id = models.IntegerField(blank=True, null=True)
    admin_id = models.IntegerField(blank=True, null=True)
    type = models.CharField(max_length=8, blank=True, null=True)
    this_trigger = models.CharField(max_length=100, blank=True, null=True)
    credit = models.IntegerField(blank=True, null=True)
    actual_date_earned = models.DateTimeField(blank=True, null=True)
    dateadded = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_badgeos_points'


class WpBadgeosRanks(models.Model):
    rank_id = models.IntegerField(blank=True, null=True)
    rank_type = models.CharField(max_length=100, blank=True, null=True)
    rank_title = models.TextField(blank=True, null=True)
    credit_id = models.IntegerField(blank=True, null=True)
    credit_amount = models.IntegerField(blank=True, null=True)
    user_id = models.IntegerField(blank=True, null=True)
    admin_id = models.IntegerField(blank=True, null=True)
    this_trigger = models.CharField(max_length=100, blank=True, null=True)
    priority = models.IntegerField()
    actual_date_earned = models.DateTimeField(blank=True, null=True)
    dateadded = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_badgeos_ranks'


class WpCommentmeta(models.Model):
    meta_id = models.BigAutoField(primary_key=True)
    comment_id = models.PositiveBigIntegerField()
    meta_key = models.CharField(max_length=255, blank=True, null=True)
    meta_value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_commentmeta'


class WpComments(models.Model):
    comment_id = models.BigAutoField(db_column='comment_ID', primary_key=True)  # Field name made lowercase.
    comment_post_id = models.PositiveBigIntegerField(db_column='comment_post_ID')  # Field name made lowercase.
    comment_author = models.TextField()
    comment_author_email = models.CharField(max_length=100)
    comment_author_url = models.CharField(max_length=200)
    comment_author_ip = models.CharField(db_column='comment_author_IP', max_length=100)  # Field name made lowercase.
    comment_date = models.DateTimeField()
    comment_date_gmt = models.DateTimeField()
    comment_content = models.TextField()
    comment_karma = models.IntegerField()
    comment_approved = models.CharField(max_length=20)
    comment_agent = models.CharField(max_length=255)
    comment_type = models.CharField(max_length=20)
    comment_parent = models.PositiveBigIntegerField()
    user_id = models.PositiveBigIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_comments'


class WpFaUserLogins(models.Model):
    session_token = models.CharField(max_length=100)
    user_id = models.IntegerField()
    username = models.CharField(max_length=200)
    time_login = models.DateTimeField()
    time_logout = models.DateTimeField(blank=True, null=True)
    time_last_seen = models.DateTimeField()
    ip_address = models.CharField(max_length=200)
    browser = models.CharField(max_length=200)
    browser_version = models.CharField(max_length=100)
    operating_system = models.CharField(max_length=100)
    country_name = models.CharField(max_length=200)
    country_code = models.CharField(max_length=200)
    timezone = models.CharField(max_length=200)
    old_role = models.CharField(max_length=200)
    user_agent = models.TextField()
    geo_response = models.TextField()
    login_status = models.CharField(max_length=50)
    is_super_admin = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_fa_user_logins'


class WpForumAds(models.Model):
    name = models.CharField(max_length=255)
    code = models.TextField(blank=True, null=True)
    active = models.IntegerField()
    locations = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_forum_ads'


class WpForumForums(models.Model):
    name = models.CharField(max_length=255)
    parent_id = models.IntegerField()
    parent_forum = models.IntegerField()
    description = models.CharField(max_length=255)
    icon = models.CharField(max_length=255)
    sort = models.IntegerField()
    forum_status = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'wp_forum_forums'


class WpForumPolls(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    multiple = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_forum_polls'


class WpForumPollsOptions(models.Model):
    poll_id = models.IntegerField()
    title = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'wp_forum_polls_options'


class WpForumPollsVotes(models.Model):
    poll_id = models.IntegerField(primary_key=True)  # The composite primary key (poll_id, option_id, user_id) found, that is not supported. The first column is selected.
    option_id = models.IntegerField()
    user_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_forum_polls_votes'
        unique_together = (('poll_id', 'option_id', 'user_id'),)


class WpForumPosts(models.Model):
    text = models.TextField(blank=True, null=True)
    parent_id = models.IntegerField()
    forum_id = models.IntegerField()
    date = models.DateTimeField()
    date_edit = models.DateTimeField()
    author_id = models.IntegerField()
    author_edit = models.IntegerField()
    uploads = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_forum_posts'


class WpForumReactions(models.Model):
    post_id = models.IntegerField(primary_key=True)  # The composite primary key (post_id, user_id) found, that is not supported. The first column is selected.
    user_id = models.IntegerField()
    reaction = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'wp_forum_reactions'
        unique_together = (('post_id', 'user_id'),)


class WpForumReports(models.Model):
    post_id = models.IntegerField(primary_key=True)  # The composite primary key (post_id, reporter_id) found, that is not supported. The first column is selected.
    reporter_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_forum_reports'
        unique_together = (('post_id', 'reporter_id'),)


class WpForumTopics(models.Model):
    parent_id = models.IntegerField()
    author_id = models.IntegerField()
    views = models.IntegerField()
    name = models.CharField(max_length=255)
    sticky = models.IntegerField()
    closed = models.IntegerField()
    approved = models.IntegerField()
    slug = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'wp_forum_topics'


class WpGfDraftSubmissions(models.Model):
    uuid = models.CharField(primary_key=True, max_length=32)
    email = models.CharField(max_length=255, blank=True, null=True)
    form_id = models.PositiveIntegerField()
    date_created = models.DateTimeField()
    ip = models.CharField(max_length=45)
    source_url = models.TextField()
    submission = models.TextField()

    class Meta:
        managed = False
        db_table = 'wp_gf_draft_submissions'


class WpGfEntry(models.Model):
    form_id = models.PositiveIntegerField()
    post_id = models.PositiveBigIntegerField(blank=True, null=True)
    date_created = models.DateTimeField()
    date_updated = models.DateTimeField(blank=True, null=True)
    is_starred = models.IntegerField()
    is_read = models.IntegerField()
    ip = models.CharField(max_length=45)
    source_url = models.CharField(max_length=200)
    user_agent = models.CharField(max_length=250)
    currency = models.CharField(max_length=5, blank=True, null=True)
    payment_status = models.CharField(max_length=15, blank=True, null=True)
    payment_date = models.DateTimeField(blank=True, null=True)
    payment_amount = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
    payment_method = models.CharField(max_length=30, blank=True, null=True)
    transaction_id = models.CharField(max_length=50, blank=True, null=True)
    is_fulfilled = models.IntegerField(blank=True, null=True)
    created_by = models.PositiveBigIntegerField(blank=True, null=True)
    transaction_type = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'wp_gf_entry'


class WpGfEntryMeta(models.Model):
    id = models.BigAutoField(primary_key=True)
    form_id = models.PositiveIntegerField()
    entry_id = models.PositiveBigIntegerField()
    meta_key = models.CharField(max_length=255, blank=True, null=True)
    meta_value = models.TextField(blank=True, null=True)
    item_index = models.CharField(max_length=60, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_gf_entry_meta'


class WpGfEntryNotes(models.Model):
    entry_id = models.PositiveIntegerField()
    user_name = models.CharField(max_length=250, blank=True, null=True)
    user_id = models.BigIntegerField(blank=True, null=True)
    date_created = models.DateTimeField()
    value = models.TextField(blank=True, null=True)
    note_type = models.CharField(max_length=50, blank=True, null=True)
    sub_type = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_gf_entry_notes'


class WpGfForm(models.Model):
    title = models.CharField(max_length=150)
    date_created = models.DateTimeField()
    date_updated = models.DateTimeField(blank=True, null=True)
    is_active = models.IntegerField()
    is_trash = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_gf_form'


class WpGfFormMeta(models.Model):
    form_id = models.PositiveIntegerField(primary_key=True)
    display_meta = models.TextField(blank=True, null=True)
    entries_grid_meta = models.TextField(blank=True, null=True)
    confirmations = models.TextField(blank=True, null=True)
    notifications = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_gf_form_meta'


class WpGfFormRevisions(models.Model):
    id = models.BigAutoField(primary_key=True)
    form_id = models.PositiveIntegerField()
    display_meta = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'wp_gf_form_revisions'


class WpGfFormView(models.Model):
    id = models.BigAutoField(primary_key=True)
    form_id = models.PositiveIntegerField()
    date_created = models.DateTimeField()
    ip = models.CharField(max_length=15, blank=True, null=True)
    count = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_gf_form_view'


class WpIclBackgroundTask(models.Model):
    task_id = models.BigAutoField(primary_key=True)
    task_type = models.CharField(max_length=500)
    task_status = models.PositiveSmallIntegerField()
    starting_date = models.DateTimeField(blank=True, null=True)
    total_count = models.PositiveIntegerField()
    completed_count = models.PositiveIntegerField()
    completed_ids = models.TextField(blank=True, null=True)
    payload = models.TextField(blank=True, null=True)
    retry_count = models.PositiveSmallIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_icl_background_task'


class WpIclContentStatus(models.Model):
    rid = models.BigIntegerField(primary_key=True)
    nid = models.BigIntegerField()
    timestamp = models.DateTimeField()
    md5 = models.CharField(max_length=32)

    class Meta:
        managed = False
        db_table = 'wp_icl_content_status'


class WpIclCoreStatus(models.Model):
    id = models.BigAutoField(primary_key=True)
    rid = models.BigIntegerField()
    module = models.CharField(max_length=16)
    origin = models.CharField(max_length=64)
    target = models.CharField(max_length=64)
    status = models.SmallIntegerField()
    tp_revision = models.IntegerField()
    ts_status = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_icl_core_status'


class WpIclFlags(models.Model):
    lang_code = models.CharField(unique=True, max_length=10)
    flag = models.CharField(max_length=32)
    from_template = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_icl_flags'


class WpIclLanguages(models.Model):
    code = models.CharField(unique=True, max_length=7)
    english_name = models.CharField(unique=True, max_length=128)
    major = models.IntegerField()
    active = models.IntegerField()
    default_locale = models.CharField(max_length=35, blank=True, null=True)
    tag = models.CharField(max_length=35, blank=True, null=True)
    encode_url = models.IntegerField()
    country = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_icl_languages'


class WpIclLanguagesTranslations(models.Model):
    language_code = models.CharField(max_length=7)
    display_language_code = models.CharField(max_length=7)
    name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'wp_icl_languages_translations'
        unique_together = (('language_code', 'display_language_code'),)


class WpIclLinksPostToPost(models.Model):
    id_from = models.PositiveBigIntegerField(primary_key=True)  # The composite primary key (id_from, id_to) found, that is not supported. The first column is selected.
    id_to = models.PositiveBigIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_icl_links_post_to_post'
        unique_together = (('id_from', 'id_to'),)


class WpIclLinksPostToTerm(models.Model):
    id_from = models.PositiveBigIntegerField(primary_key=True)  # The composite primary key (id_from, id_to) found, that is not supported. The first column is selected.
    id_to = models.PositiveBigIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_icl_links_post_to_term'
        unique_together = (('id_from', 'id_to'),)


class WpIclLocaleMap(models.Model):
    code = models.CharField(primary_key=True, max_length=7)  # The composite primary key (code, locale) found, that is not supported. The first column is selected.
    locale = models.CharField(max_length=35)

    class Meta:
        managed = False
        db_table = 'wp_icl_locale_map'
        unique_together = (('code', 'locale'),)


class WpIclMessageStatus(models.Model):
    id = models.BigAutoField(primary_key=True)
    rid = models.PositiveBigIntegerField(unique=True)
    object_id = models.PositiveBigIntegerField()
    from_language = models.CharField(max_length=10)
    to_language = models.CharField(max_length=10)
    timestamp = models.DateTimeField()
    md5 = models.CharField(max_length=32)
    object_type = models.CharField(max_length=64)
    status = models.SmallIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_icl_message_status'


class WpIclMoFilesDomains(models.Model):
    file_path = models.CharField(max_length=250)
    file_path_md5 = models.CharField(unique=True, max_length=32)
    domain = models.CharField(max_length=160)
    status = models.CharField(max_length=20)
    num_of_strings = models.IntegerField()
    last_modified = models.IntegerField()
    component_type = models.CharField(max_length=6)
    component_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_icl_mo_files_domains'


class WpIclNode(models.Model):
    nid = models.BigIntegerField(primary_key=True)
    md5 = models.CharField(max_length=32)
    links_fixed = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_icl_node'


class WpIclReminders(models.Model):
    id = models.BigIntegerField(primary_key=True)
    message = models.TextField()
    url = models.TextField()
    can_delete = models.IntegerField()
    show = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_icl_reminders'


class WpIclStringBatches(models.Model):
    id = models.BigAutoField(primary_key=True)
    string_id = models.PositiveBigIntegerField()
    batch_id = models.PositiveBigIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_icl_string_batches'


class WpIclStringPackages(models.Model):
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    kind_slug = models.CharField(max_length=160)
    kind = models.CharField(max_length=160)
    name = models.CharField(max_length=160)
    title = models.CharField(max_length=160)
    edit_link = models.TextField()
    view_link = models.TextField()
    post_id = models.IntegerField(blank=True, null=True)
    word_count = models.CharField(max_length=2000, blank=True, null=True)
    translator_note = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_icl_string_packages'


class WpIclStringPositions(models.Model):
    id = models.BigAutoField(primary_key=True)
    string_id = models.BigIntegerField()
    kind = models.IntegerField(blank=True, null=True)
    position_in_page = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'wp_icl_string_positions'


class WpIclStringStatus(models.Model):
    id = models.BigAutoField(primary_key=True)
    rid = models.BigIntegerField()
    string_translation_id = models.BigIntegerField()
    timestamp = models.DateTimeField()
    md5 = models.CharField(max_length=32)

    class Meta:
        managed = False
        db_table = 'wp_icl_string_status'


class WpIclStringTranslations(models.Model):
    id = models.BigAutoField(primary_key=True)
    string_id = models.PositiveBigIntegerField()
    language = models.CharField(max_length=10)
    status = models.IntegerField()
    value = models.TextField(blank=True, null=True)
    mo_string = models.TextField(blank=True, null=True)
    translator_id = models.PositiveBigIntegerField(blank=True, null=True)
    translation_service = models.CharField(max_length=16)
    batch_id = models.IntegerField()
    translation_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'wp_icl_string_translations'
        unique_together = (('string_id', 'language'),)


class WpIclStrings(models.Model):
    id = models.BigAutoField(primary_key=True)
    language = models.CharField(max_length=7)
    context = models.CharField(max_length=160)
    name = models.CharField(max_length=160)
    value = models.TextField()
    string_package_id = models.PositiveBigIntegerField(blank=True, null=True)
    location = models.PositiveBigIntegerField(blank=True, null=True)
    wrap_tag = models.CharField(max_length=16)
    type = models.CharField(max_length=40)
    title = models.CharField(max_length=160, blank=True, null=True)
    status = models.IntegerField()
    gettext_context = models.TextField()
    domain_name_context_md5 = models.CharField(unique=True, max_length=32)
    translation_priority = models.CharField(max_length=160)
    word_count = models.PositiveIntegerField(blank=True, null=True)
    string_type = models.IntegerField()
    component_id = models.CharField(max_length=500, blank=True, null=True)
    component_type = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_icl_strings'


class WpIclTranslate(models.Model):
    tid = models.BigAutoField(primary_key=True)
    job_id = models.PositiveBigIntegerField()
    content_id = models.PositiveBigIntegerField()
    timestamp = models.DateTimeField()
    field_type = models.CharField(max_length=160)
    field_wrap_tag = models.CharField(max_length=16)
    field_format = models.CharField(max_length=16)
    field_translate = models.IntegerField()
    field_data = models.TextField()
    field_data_translated = models.TextField()
    field_finished = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_icl_translate'


class WpIclTranslateJob(models.Model):
    job_id = models.BigAutoField(primary_key=True)
    rid = models.PositiveBigIntegerField()
    translator_id = models.PositiveIntegerField()
    translated = models.PositiveIntegerField()
    manager_id = models.PositiveIntegerField()
    revision = models.PositiveIntegerField(blank=True, null=True)
    title = models.CharField(max_length=160, blank=True, null=True)
    deadline_date = models.DateTimeField(blank=True, null=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    editor = models.CharField(max_length=16, blank=True, null=True)
    editor_job_id = models.PositiveBigIntegerField(blank=True, null=True)
    edit_timestamp = models.PositiveIntegerField(blank=True, null=True)
    automatic = models.PositiveIntegerField()
    ate_sync_count = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_icl_translate_job'


class WpIclTranslationBatches(models.Model):
    batch_name = models.TextField()
    tp_id = models.IntegerField(blank=True, null=True)
    ts_url = models.TextField(blank=True, null=True)
    last_update = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_icl_translation_batches'


class WpIclTranslationDownloads(models.Model):
    editor_job_id = models.PositiveBigIntegerField(primary_key=True)
    download_url = models.CharField(max_length=2000)
    lock_timestamp = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_icl_translation_downloads'


class WpIclTranslationStatus(models.Model):
    rid = models.BigAutoField(primary_key=True)
    translation_id = models.BigIntegerField(unique=True)
    status = models.IntegerField()
    translator_id = models.BigIntegerField()
    needs_update = models.IntegerField()
    md5 = models.CharField(max_length=32)
    translation_service = models.CharField(max_length=16)
    batch_id = models.IntegerField()
    translation_package = models.TextField()
    timestamp = models.DateTimeField()
    links_fixed = models.IntegerField()
    field_prevstate = models.TextField(db_column='_prevstate', blank=True, null=True)  # Field renamed because it started with '_'.
    uuid = models.CharField(max_length=36, blank=True, null=True)
    tp_id = models.IntegerField(blank=True, null=True)
    tp_revision = models.IntegerField()
    ts_status = models.TextField(blank=True, null=True)
    review_status = models.CharField(max_length=12, blank=True, null=True)
    ate_comm_retry_count = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_icl_translation_status'


class WpIclTranslations(models.Model):
    translation_id = models.BigAutoField(primary_key=True)
    element_type = models.CharField(max_length=60)
    element_id = models.BigIntegerField(blank=True, null=True)
    trid = models.BigIntegerField()
    language_code = models.CharField(max_length=7)
    source_language_code = models.CharField(max_length=7, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_icl_translations'
        unique_together = (('trid', 'language_code'), ('element_type', 'element_id'),)


class WpLeaderboard(models.Model):
    user_id = models.BigIntegerField(blank=True, null=True)
    point = models.IntegerField(blank=True, null=True)
    older_point = models.IntegerField(blank=True, null=True)
    last_update = models.DateTimeField()
    completed_courses = models.IntegerField(blank=True, null=True)
    total_courses = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_leaderboard'


class WpLearndashProQuizCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = 'wp_learndash_pro_quiz_category'


class WpLearndashProQuizForm(models.Model):
    form_id = models.AutoField(primary_key=True)
    quiz_id = models.IntegerField()
    fieldname = models.CharField(max_length=100)
    type = models.IntegerField()
    required = models.PositiveIntegerField()
    sort = models.IntegerField()
    data = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_learndash_pro_quiz_form'


class WpLearndashProQuizLock(models.Model):
    quiz_id = models.IntegerField(primary_key=True)  # The composite primary key (quiz_id, lock_ip, user_id, lock_type) found, that is not supported. The first column is selected.
    lock_ip = models.CharField(max_length=100)
    user_id = models.PositiveBigIntegerField()
    lock_type = models.PositiveIntegerField()
    lock_date = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_learndash_pro_quiz_lock'
        unique_together = (('quiz_id', 'lock_ip', 'user_id', 'lock_type'),)


class WpLearndashProQuizMaster(models.Model):
    name = models.TextField()
    text = models.TextField()
    result_text = models.TextField()
    result_grade_enabled = models.IntegerField()
    title_hidden = models.IntegerField()
    btn_restart_quiz_hidden = models.IntegerField()
    btn_view_question_hidden = models.IntegerField()
    question_random = models.IntegerField()
    answer_random = models.IntegerField()
    time_limit = models.IntegerField()
    statistics_on = models.IntegerField()
    statistics_ip_lock = models.PositiveIntegerField()
    show_points = models.IntegerField()
    quiz_run_once = models.IntegerField()
    quiz_run_once_type = models.IntegerField()
    quiz_run_once_cookie = models.IntegerField()
    quiz_run_once_time = models.PositiveIntegerField()
    numbered_answer = models.IntegerField()
    hide_answer_message_box = models.IntegerField()
    disabled_answer_mark = models.IntegerField()
    show_max_question = models.IntegerField()
    show_max_question_value = models.PositiveIntegerField()
    show_max_question_percent = models.IntegerField()
    toplist_activated = models.IntegerField()
    toplist_data = models.TextField()
    show_average_result = models.IntegerField()
    prerequisite = models.IntegerField()
    quiz_modus = models.PositiveIntegerField()
    show_review_question = models.IntegerField()
    quiz_summary_hide = models.IntegerField()
    skip_question_disabled = models.IntegerField()
    email_notification = models.PositiveIntegerField()
    user_email_notification = models.PositiveIntegerField()
    show_category_score = models.PositiveIntegerField()
    hide_result_correct_question = models.PositiveIntegerField()
    hide_result_quiz_time = models.PositiveIntegerField()
    hide_result_points = models.PositiveIntegerField()
    autostart = models.PositiveIntegerField()
    forcing_question_solve = models.PositiveIntegerField()
    hide_question_position_overview = models.PositiveIntegerField()
    hide_question_numbering = models.PositiveIntegerField()
    form_activated = models.PositiveIntegerField()
    form_show_position = models.PositiveIntegerField()
    start_only_registered_user = models.PositiveIntegerField()
    questions_per_page = models.PositiveIntegerField()
    sort_categories = models.PositiveIntegerField()
    show_category = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_learndash_pro_quiz_master'


class WpLearndashProQuizPrerequisite(models.Model):
    prerequisite_quiz_id = models.IntegerField(primary_key=True)  # The composite primary key (prerequisite_quiz_id, quiz_id) found, that is not supported. The first column is selected.
    quiz_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_learndash_pro_quiz_prerequisite'
        unique_together = (('prerequisite_quiz_id', 'quiz_id'),)


class WpLearndashProQuizQuestion(models.Model):
    quiz_id = models.IntegerField()
    online = models.PositiveIntegerField()
    previous_id = models.IntegerField()
    sort = models.PositiveSmallIntegerField()
    title = models.TextField()
    points = models.IntegerField()
    question = models.TextField()
    correct_msg = models.TextField()
    incorrect_msg = models.TextField()
    correct_same_text = models.IntegerField()
    tip_enabled = models.IntegerField()
    tip_msg = models.TextField()
    answer_type = models.CharField(max_length=50)
    show_points_in_box = models.IntegerField()
    answer_points_activated = models.IntegerField()
    answer_data = models.TextField()
    category_id = models.PositiveIntegerField()
    answer_points_diff_modus_activated = models.PositiveIntegerField()
    disable_correct = models.PositiveIntegerField()
    matrix_sort_answer_criteria_width = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_learndash_pro_quiz_question'


class WpLearndashProQuizStatistic(models.Model):
    statistic_ref_id = models.PositiveIntegerField(primary_key=True)  # The composite primary key (statistic_ref_id, question_id) found, that is not supported. The first column is selected.
    question_id = models.IntegerField()
    question_post_id = models.IntegerField()
    correct_count = models.PositiveIntegerField()
    incorrect_count = models.PositiveIntegerField()
    hint_count = models.PositiveIntegerField()
    points = models.PositiveIntegerField()
    question_time = models.PositiveIntegerField()
    answer_data = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_learndash_pro_quiz_statistic'
        unique_together = (('statistic_ref_id', 'question_id'),)


class WpLearndashProQuizStatisticRef(models.Model):
    statistic_ref_id = models.AutoField(primary_key=True)
    quiz_id = models.IntegerField()
    quiz_post_id = models.IntegerField()
    course_post_id = models.IntegerField()
    user_id = models.PositiveBigIntegerField()
    create_time = models.IntegerField()
    is_old = models.PositiveIntegerField()
    form_data = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_learndash_pro_quiz_statistic_ref'


class WpLearndashProQuizTemplate(models.Model):
    template_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    type = models.PositiveIntegerField()
    data = models.TextField()

    class Meta:
        managed = False
        db_table = 'wp_learndash_pro_quiz_template'


class WpLearndashProQuizToplist(models.Model):
    toplist_id = models.AutoField(primary_key=True)  # The composite primary key (toplist_id, quiz_id) found, that is not supported. The first column is selected.
    quiz_id = models.IntegerField()
    date = models.PositiveIntegerField()
    user_id = models.PositiveBigIntegerField()
    name = models.CharField(max_length=30)
    email = models.CharField(max_length=200)
    points = models.PositiveIntegerField()
    result = models.FloatField()
    ip = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'wp_learndash_pro_quiz_toplist'
        unique_together = (('toplist_id', 'quiz_id'),)


class WpLearndashUserActivity(models.Model):
    activity_id = models.BigAutoField(primary_key=True)
    user_id = models.PositiveBigIntegerField()
    post_id = models.PositiveBigIntegerField()
    course_id = models.PositiveBigIntegerField()
    activity_type = models.CharField(max_length=50, blank=True, null=True)
    activity_status = models.PositiveIntegerField(blank=True, null=True)
    activity_started = models.PositiveIntegerField(blank=True, null=True)
    activity_completed = models.PositiveIntegerField(blank=True, null=True)
    activity_updated = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_learndash_user_activity'


class WpLearndashUserActivityMeta(models.Model):
    activity_meta_id = models.BigAutoField(primary_key=True)
    activity_id = models.PositiveBigIntegerField()
    activity_meta_key = models.CharField(max_length=255, blank=True, null=True)
    activity_meta_value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_learndash_user_activity_meta'


class WpLinks(models.Model):
    link_id = models.BigAutoField(primary_key=True)
    link_url = models.CharField(max_length=255)
    link_name = models.CharField(max_length=255)
    link_image = models.CharField(max_length=255)
    link_target = models.CharField(max_length=25)
    link_description = models.CharField(max_length=255)
    link_visible = models.CharField(max_length=20)
    link_owner = models.PositiveBigIntegerField()
    link_rating = models.IntegerField()
    link_updated = models.DateTimeField()
    link_rel = models.CharField(max_length=255)
    link_notes = models.TextField()
    link_rss = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'wp_links'


class WpMessageLog(models.Model):
    messageid = models.CharField(db_column='messageID', max_length=255)  # Field name made lowercase.
    date_sent = models.DateField()
    sent_at = models.DateTimeField()
    user_id = models.CharField(max_length=100)
    course_id = models.CharField(max_length=100)
    message_type = models.CharField(max_length=50)
    message_status = models.CharField(max_length=50)
    message_content = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_message_log'


class WpMoSpAttributes(models.Model):
    id = models.BigAutoField(primary_key=True)
    mo_sp = models.ForeignKey('WpMoSpData', models.DO_NOTHING, blank=True, null=True)
    mo_sp_attr_name = models.TextField()
    mo_sp_attr_value = models.TextField()
    mo_attr_type = models.SmallIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_mo_sp_attributes'


class WpMoSpData(models.Model):
    id = models.BigAutoField(primary_key=True)
    mo_idp_sp_name = models.TextField()
    mo_idp_sp_issuer = models.TextField()
    mo_idp_acs_url = models.TextField()
    mo_idp_cert = models.TextField(blank=True, null=True)
    mo_idp_cert_encrypt = models.TextField(blank=True, null=True)
    mo_idp_nameid_format = models.TextField()
    mo_idp_nameid_attr = models.CharField(max_length=55)
    mo_idp_response_signed = models.SmallIntegerField(blank=True, null=True)
    mo_idp_assertion_signed = models.SmallIntegerField(blank=True, null=True)
    mo_idp_encrypted_assertion = models.SmallIntegerField(blank=True, null=True)
    mo_idp_enable_group_mapping = models.SmallIntegerField(blank=True, null=True)
    mo_idp_default_relaystate = models.TextField(db_column='mo_idp_default_relayState', blank=True, null=True)  # Field name made lowercase.
    mo_idp_logout_url = models.TextField(blank=True, null=True)
    mo_idp_logout_binding_type = models.CharField(max_length=15)
    mo_idp_protocol_type = models.TextField()

    class Meta:
        managed = False
        db_table = 'wp_mo_sp_data'


class WpMoosOauthPublicKeys(models.Model):
    client_id = models.CharField(max_length=80, blank=True, null=True)
    public_key = models.CharField(max_length=8000, blank=True, null=True)
    private_key = models.CharField(max_length=8000, blank=True, null=True)
    encryption_algorithm = models.CharField(max_length=80, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_moos_oauth_public_keys'


class WpOptions(models.Model):
    option_id = models.BigAutoField(primary_key=True)
    option_name = models.CharField(unique=True, max_length=191)
    option_value = models.TextField()
    autoload = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'wp_options'


class WpP2P(models.Model):
    p2p_id = models.BigAutoField(primary_key=True)
    p2p_from = models.PositiveBigIntegerField()
    p2p_to = models.PositiveBigIntegerField()
    p2p_type = models.CharField(max_length=44)

    class Meta:
        managed = False
        db_table = 'wp_p2p'


class WpP2Pmeta(models.Model):
    meta_id = models.BigAutoField(primary_key=True)
    p2p_id = models.PositiveBigIntegerField()
    meta_key = models.CharField(max_length=255, blank=True, null=True)
    meta_value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_p2pmeta'


class WpPostmeta(models.Model):
    meta_id = models.BigAutoField(primary_key=True)
    post_id = models.PositiveBigIntegerField()
    meta_key = models.CharField(max_length=255, blank=True, null=True)
    meta_value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_postmeta'


class WpPosts(models.Model):
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    post_author = models.PositiveBigIntegerField()
    post_date = models.DateTimeField()
    post_date_gmt = models.DateTimeField()
    post_content = models.TextField()
    post_title = models.TextField()
    post_excerpt = models.TextField()
    post_status = models.CharField(max_length=20)
    comment_status = models.CharField(max_length=20)
    ping_status = models.CharField(max_length=20)
    post_password = models.CharField(max_length=255)
    post_name = models.CharField(max_length=200)
    to_ping = models.TextField()
    pinged = models.TextField()
    post_modified = models.DateTimeField()
    post_modified_gmt = models.DateTimeField()
    post_content_filtered = models.TextField()
    post_parent = models.PositiveBigIntegerField()
    guid = models.CharField(max_length=255)
    menu_order = models.IntegerField()
    post_type = models.CharField(max_length=20)
    post_mime_type = models.CharField(max_length=100)
    comment_count = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_posts'


class WpPpressCoupons(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=50)
    description = models.TextField(blank=True, null=True)
    coupon_application = models.CharField(max_length=50)
    type = models.CharField(max_length=50)
    amount = models.TextField()
    unit = models.CharField(max_length=50)
    plan_ids = models.TextField(blank=True, null=True)
    usage_limit = models.PositiveIntegerField(blank=True, null=True)
    status = models.CharField(max_length=5)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_ppress_coupons'


class WpPpressCustomers(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.PositiveBigIntegerField(unique=True, blank=True, null=True)
    private_note = models.TextField(blank=True, null=True)
    total_spend = models.DecimalField(max_digits=18, decimal_places=9)
    purchase_count = models.PositiveBigIntegerField()
    last_login = models.DateTimeField(blank=True, null=True)
    date_created = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_ppress_customers'


class WpPpressForms(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100)
    form_id = models.BigIntegerField()
    form_type = models.CharField(max_length=20)
    builder_type = models.CharField(max_length=20)
    date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'wp_ppress_forms'


class WpPpressFormsmeta(models.Model):
    meta_id = models.BigAutoField(primary_key=True)
    form_id = models.BigIntegerField()
    form_type = models.CharField(max_length=20, blank=True, null=True)
    meta_key = models.CharField(max_length=255, blank=True, null=True)
    meta_value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_ppress_formsmeta'


class WpPpressMetaData(models.Model):
    id = models.BigAutoField(primary_key=True)
    meta_key = models.CharField(max_length=50, blank=True, null=True)
    meta_value = models.TextField(blank=True, null=True)
    flag = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_ppress_meta_data'


class WpPpressOrdermeta(models.Model):
    meta_id = models.BigAutoField(primary_key=True)
    ppress_order_id = models.BigIntegerField()
    meta_key = models.CharField(max_length=255, blank=True, null=True)
    meta_value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_ppress_ordermeta'


class WpPpressOrders(models.Model):
    id = models.BigAutoField(primary_key=True)
    order_key = models.CharField(unique=True, max_length=64)
    plan_id = models.PositiveBigIntegerField()
    customer_id = models.PositiveBigIntegerField()
    subscription_id = models.PositiveBigIntegerField()
    order_type = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    coupon_code = models.CharField(max_length=20, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=26, decimal_places=8)
    tax = models.DecimalField(max_digits=26, decimal_places=8)
    tax_rate = models.TextField()
    discount = models.DecimalField(max_digits=26, decimal_places=8)
    total = models.DecimalField(max_digits=26, decimal_places=8)
    billing_address = models.CharField(max_length=200)
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=100)
    billing_postcode = models.CharField(max_length=100)
    billing_country = models.CharField(max_length=100)
    billing_phone = models.CharField(max_length=100)
    mode = models.CharField(max_length=4)
    currency = models.CharField(max_length=10)
    ip_address = models.CharField(max_length=100)
    date_created = models.DateTimeField()
    date_completed = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_ppress_orders'


class WpPpressPlans(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=26, decimal_places=8)
    billing_frequency = models.CharField(max_length=50)
    subscription_length = models.CharField(max_length=50)
    total_payments = models.IntegerField(blank=True, null=True)
    signup_fee = models.DecimalField(max_digits=26, decimal_places=8, blank=True, null=True)
    free_trial = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=5)
    meta_data = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_ppress_plans'


class WpPpressSessions(models.Model):
    session_id = models.BigAutoField(unique=True)
    session_key = models.CharField(primary_key=True, max_length=32)
    session_value = models.TextField()
    session_expiry = models.PositiveBigIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_ppress_sessions'


class WpPpressSubscriptions(models.Model):
    id = models.BigAutoField(primary_key=True)
    parent_order_id = models.PositiveBigIntegerField()
    plan_id = models.PositiveBigIntegerField()
    customer_id = models.PositiveBigIntegerField()
    billing_frequency = models.CharField(max_length=50)
    initial_amount = models.DecimalField(max_digits=26, decimal_places=8)
    initial_tax_rate = models.TextField()
    initial_tax = models.TextField()
    recurring_amount = models.DecimalField(max_digits=26, decimal_places=8)
    recurring_tax_rate = models.TextField()
    recurring_tax = models.TextField()
    total_payments = models.PositiveBigIntegerField()
    trial_period = models.CharField(max_length=50, blank=True, null=True)
    profile_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    created_date = models.DateTimeField(blank=True, null=True)
    expiration_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_ppress_subscriptions'


class WpSncFileInfo(models.Model):
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    file_name = models.CharField(max_length=100)
    type = models.CharField(max_length=15)
    url = models.CharField(max_length=255)
    subtype = models.CharField(max_length=15, blank=True, null=True)
    version = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_snc_file_info'


class WpSncPostRelationship(models.Model):
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    snc = models.ForeignKey(WpSncFileInfo, models.DO_NOTHING)
    post = models.ForeignKey(WpPosts, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'wp_snc_post_relationship'


class WpTcCourseAccess(models.Model):
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    course_id = models.BigIntegerField()
    user_id = models.BigIntegerField()
    group_id = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_tc_course_access'


class WpTermRelationships(models.Model):
    object_id = models.PositiveBigIntegerField(primary_key=True)  # The composite primary key (object_id, term_taxonomy_id) found, that is not supported. The first column is selected.
    term_taxonomy_id = models.PositiveBigIntegerField()
    term_order = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_term_relationships'
        unique_together = (('object_id', 'term_taxonomy_id'),)


class WpTermTaxonomy(models.Model):
    term_taxonomy_id = models.BigAutoField(primary_key=True)
    term_id = models.PositiveBigIntegerField()
    taxonomy = models.CharField(max_length=32)
    description = models.TextField()
    parent = models.PositiveBigIntegerField()
    count = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_term_taxonomy'
        unique_together = (('term_id', 'taxonomy'),)


class WpTermmeta(models.Model):
    meta_id = models.BigAutoField(primary_key=True)
    term_id = models.PositiveBigIntegerField()
    meta_key = models.CharField(max_length=255, blank=True, null=True)
    meta_value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_termmeta'


class WpTerms(models.Model):
    term_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)
    term_group = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'wp_terms'


class WpUotincanQuiz(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(WpPosts, models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey('WpUsers', models.DO_NOTHING)
    course = models.ForeignKey(WpPosts, models.DO_NOTHING, related_name='wpuotincanquiz_course_set', blank=True, null=True)
    lesson = models.ForeignKey(WpPosts, models.DO_NOTHING, related_name='wpuotincanquiz_lesson_set', blank=True, null=True)
    module = models.CharField(max_length=255, blank=True, null=True)
    module_name = models.CharField(max_length=255, blank=True, null=True)
    activity_id = models.CharField(max_length=255, blank=True, null=True)
    activity_name = models.CharField(max_length=255, blank=True, null=True)
    result = models.IntegerField(blank=True, null=True)
    max_score = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    min_score = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    raw_score = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    scaled_score = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    correct_response = models.CharField(max_length=255, blank=True, null=True)
    available_responses = models.CharField(max_length=255, blank=True, null=True)
    user_response = models.TextField(blank=True, null=True)
    xstored = models.DateTimeField(blank=True, null=True)
    duration = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_uotincan_quiz'


class WpUotincanReporting(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(WpPosts, models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey('WpUsers', models.DO_NOTHING)
    course = models.ForeignKey(WpPosts, models.DO_NOTHING, related_name='wpuotincanreporting_course_set', blank=True, null=True)
    lesson = models.ForeignKey(WpPosts, models.DO_NOTHING, related_name='wpuotincanreporting_lesson_set', blank=True, null=True)
    module = models.CharField(max_length=255, blank=True, null=True)
    module_name = models.CharField(max_length=255, blank=True, null=True)
    target = models.CharField(max_length=255, blank=True, null=True)
    target_name = models.CharField(max_length=255, blank=True, null=True)
    verb = models.CharField(max_length=50, blank=True, null=True)
    result = models.IntegerField(blank=True, null=True)
    minimum = models.IntegerField(blank=True, null=True)
    completion = models.IntegerField(blank=True, null=True)
    xstored = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_uotincan_reporting'


class WpUotincanResume(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('WpUsers', models.DO_NOTHING)
    course_id = models.PositiveBigIntegerField(blank=True, null=True)
    lesson_id = models.PositiveBigIntegerField(blank=True, null=True)
    module = models.ForeignKey(WpSncFileInfo, models.DO_NOTHING)
    state = models.CharField(max_length=50, blank=True, null=True)
    value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_uotincan_resume'


class WpUsermeta(models.Model):
    umeta_id = models.BigAutoField(primary_key=True)
    user_id = models.PositiveBigIntegerField()
    meta_key = models.CharField(max_length=255, blank=True, null=True)
    meta_value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_usermeta'


class WpUsers(models.Model):
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    user_login = models.CharField(max_length=60)
    user_pass = models.CharField(max_length=255)
    user_nicename = models.CharField(max_length=50)
    user_email = models.CharField(max_length=100, blank=True, null=True)
    user_url = models.CharField(max_length=100)
    user_registered = models.DateTimeField()
    user_activation_key = models.CharField(max_length=255)
    user_status = models.IntegerField()
    display_name = models.CharField(max_length=250)

    class Meta:
        managed = False
        db_table = 'wp_users'


class WpWpfmBackup(models.Model):
    backup_name = models.TextField(blank=True, null=True)
    backup_date = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wp_wpfm_backup'


class WpWpmailsmtpDebugEvents(models.Model):
    content = models.TextField(blank=True, null=True)
    initiator = models.TextField(blank=True, null=True)
    event_type = models.PositiveIntegerField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'wp_wpmailsmtp_debug_events'


class WpWpmailsmtpTasksMeta(models.Model):
    id = models.BigAutoField(primary_key=True)
    action = models.CharField(max_length=255)
    data = models.TextField()
    date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'wp_wpmailsmtp_tasks_meta'


class WpWpmlMails(models.Model):
    mail_id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField()
    host = models.CharField(max_length=200)
    receiver = models.CharField(max_length=200)
    subject = models.CharField(max_length=200)
    message = models.TextField(blank=True, null=True)
    headers = models.TextField(blank=True, null=True)
    attachments = models.CharField(max_length=800)
    error = models.CharField(max_length=400, blank=True, null=True)
    plugin_version = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = 'wp_wpml_mails'


class WpWprRocketCache(models.Model):
    id = models.BigAutoField(primary_key=True)
    url = models.CharField(max_length=2000)
    status = models.CharField(max_length=255)
    modified = models.DateTimeField()
    last_accessed = models.DateTimeField()
    is_locked = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'wp_wpr_rocket_cache'


class WpWprRucssUsedCss(models.Model):
    id = models.BigAutoField(primary_key=True)
    url = models.CharField(max_length=2000)
    css = models.TextField(blank=True, null=True)
    hash = models.CharField(max_length=32, blank=True, null=True)
    error_code = models.CharField(max_length=32, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    unprocessedcss = models.TextField(blank=True, null=True)
    retries = models.IntegerField()
    is_mobile = models.IntegerField()
    job_id = models.CharField(max_length=255)
    queue_name = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    modified = models.DateTimeField()
    last_accessed = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'wp_wpr_rucss_used_css'
