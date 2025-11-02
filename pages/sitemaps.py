# pages/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Blog

class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'monthly'

    def items(self):
        return ['home', 'blog_list', 'about', 'contact', 'faq', 'privacy', 'terms']

    def location(self, item):
        return reverse(item)

class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Blog.objects.filter(status=Blog.Status.PUBLISHED)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('blog_detail', kwargs={'slug': obj.slug})
