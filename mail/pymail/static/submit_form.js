function submitForm(action, previous) {
    	document.submitme.action.value = action;
		document.submitme.previous.value = previous;
    	document.submitme.submit();
}