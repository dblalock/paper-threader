 [One Weird Trick to Improve Your Semi-Weakly Supervised Semantic Segmentation Model](https://arxiv.org/abs/2205.01233)Problem
 setup is that you want to do semantic segmentation but your dataset has
 only a few images per class with pixel-level labels and many images 
with image-level class labels. They propose training an image classifier
 on the data with image-level labels and using its class predictions to 
filter which classes are even considered for pixel-level labels. Turns 
out this improves pixel-level accuracy a lot. The intuition they give is
 that pixel-level labeling with few examples mostly learns to pick up on
 local features, and so might think that cat pixels are actually horse 
pixels because they’re both covered in hair. But if the image classifier
 knows there’s no horse in this image, the model can’t make this 
mistake. I really like how simple and effective an intervention this is.


![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F2d0814a5-9d3d-4d3f-923f-bd8c7bdf10e9_1316x718.png)
![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F85857e95-71a8-4b63-a498-b7948c7dcdeb_2524x754.png)
![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F150d2038-6446-4139-9ad7-420f26d9f535_2714x582.png)
