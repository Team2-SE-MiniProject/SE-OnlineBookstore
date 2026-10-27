from django.urls import path

from . import views

app_name = "seller"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("books/add/", views.BookCreateView.as_view(), name="book-add"),
    path("books/<int:pk>/edit/", views.BookUpdateView.as_view(), name="book-edit"),
    path("books/<int:pk>/delete/", views.BookDeleteView.as_view(), name="book-delete"),
    path("analytics/", views.AnalyticsView.as_view(), name="analytics"),
    path("analytics/export.csv", views.AnalyticsExportView.as_view(), name="analytics-export"),
]
