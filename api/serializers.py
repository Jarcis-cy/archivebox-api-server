from rest_framework import serializers


class AddUrlsSerializer(serializers.Serializer):
    urls = serializers.ListField(
        child=serializers.URLField(),
        allow_empty=False,
        required=True,
        help_text="要添加的 URL 列表。例如：'https://example.com','https://example.org'"
    )
    tag = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="为添加的 URL 打上标签。例如：--tag=tag1,tag2,tag3"
    )
    depth = serializers.IntegerField(
        default=0,
        required=False,
        help_text="递归存档所有链接页面，深度为 0 或 1。例如：--depth=0",
        min_value=0,
        max_value=1
    )
    update = serializers.BooleanField(
        default=False,
        required=False,
        help_text="在添加新链接时重试之前跳过/失败的链接。例如：--update"
    )
    update_all = serializers.BooleanField(
        default=False,
        required=False,
        help_text="在完成添加新链接后，更新索引中的所有链接。例如：--update-all"
    )
    overwrite = serializers.BooleanField(
        default=False,
        required=False,
        help_text="从头开始重新存档 URL，覆盖任何现有文件。例如：--overwrite"
    )
    extractors = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            "title", "screenshot", "git", "favicon", "headers", "singlefile", "pdf", "dom", "wget", "readability",
            "mercury", "htmltotext", "media", "archive_org"
        ]),
        required=False,
        help_text="传递要使用的提取器列表，使用列表形式。例如：['title','screenshot','git']"
    )
    parser = serializers.ListField(
        child=serializers.ChoiceField(
            choices=['auto', 'pocket_api', 'readwise_reader_api', 'wallabag_atom', 'pocket_html', 'pinboard_rss',
                     'shaarli_rss', 'medium_rss', 'netscape_html', 'rss', 'json', 'jsonl', 'html', 'txt', 'url_list']),
        required=False,
        help_text="用于读取输入 URL 的解析器。例如：--parser=auto",
    )

    def validate_extractors(self, value):
        if value:
            return ",".join(value)
        return ""

    def validate_parser(self, value):
        if value:
            return ",".join(value)
        return ""

