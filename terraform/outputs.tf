output "instance_name" {
  value = google_compute_instance.app.name
}

output "instance_public_ip" {
  value = google_compute_address.app.address
}

output "deploy_user" {
  value = "deploy"
}
