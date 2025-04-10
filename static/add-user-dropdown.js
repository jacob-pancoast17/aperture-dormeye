window.addEventListener("DOMContentLoaded", () => {
	const toggleButton = document.getElementById("toggleDropdown");
	const content = document.getElementById("addUserDropdown");

	toggleButton.addEventListener("click", () => {
		const isVisible = content.style.display === "block";
		content.style.display = isVisible ? "none" : "block";
		toggleButton.textContent = isVisible ? "Add User" : "Minimize";
	});
});
