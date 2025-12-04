#!/bin/bash

for page in ./website/templates/website/*.html; do
    if [ "$page" != "./website/templates/website/index.html" ]; then
        echo "Updating: $page"
        {
            echo "{% extends 'base.html' %}"
            echo "{% load static %}"
            echo ""
            echo "{% block content %}"
            cat "$page"
            echo "{% endblock %}"
        } > "${page}.tmp"
        
        mv "${page}.tmp" "$page"
    fi
done

echo "All pages updated to extend base template!"
