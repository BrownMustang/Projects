window.onload = function() {
    document.querySelector('.spinner-border').style.display = 'none';
  };

  document.getElementById('myForm').addEventListener('submit', function(event) {
    event.preventDefault();
    // Your code to handle the form data goes here
    var height = document.getElementById('height').value;
    var weight = document.getElementById('weight').value;

    var cals = 88 + 14*weight + 4*height;
    var protiens = 1.5 * weight;
    var fats = 0.6 * weight;
    var carbs = (cals - protiens*4 - fats*9)/4;

    document.getElementById('bmr').innerHTML = "Your dialy maintainance calrories: " + cals;
    document.getElementById('protien').innerHTML = "Protein: " + protiens + " grams";
    document.getElementById('fats').innerHTML = "Fats: " + fats + " grams";
    document.getElementById('carbs').innerHTML = "Carbs: " + carbs + " grams";

  });
